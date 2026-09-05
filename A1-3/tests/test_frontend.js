const fs = require('fs');
const vm = require('vm');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const script = html.split('<script>')[1].split('</script>')[0];

function makeEl(id='') {
  const listeners = {};
  const classes = new Set(['hidden']);
  return {
    id, value:'', textContent:'', innerHTML:'', children:[], disabled:false,
    className:'', href:'', target:'', rel:'',
    classList: {
      add: (...xs)=>xs.forEach(x=>classes.add(x)),
      remove: (...xs)=>xs.forEach(x=>classes.delete(x)),
      contains: (x)=>classes.has(x),
    },
    appendChild(child){ this.children.push(child); },
    addEventListener(type, fn){ listeners[type]=fn; },
    focus(){ this.focused=true; },
    trigger(type, event={}){ return listeners[type]?.(event); },
  };
}

function setup(fetchImpl) {
  const ids = ['novelInput','analyzeBtn','btnText','loadingSpinner','errorBox','resultContainer','tagsContainer',
    'identifiedTitle','confidenceBadge','identityMeta','evidenceNote','resStory','resCharm','resWarning',
    'sourcesContainer','queriesContainer','googleSearchEntryPoint'];
  const elements = Object.fromEntries(ids.map(id=>[id, makeEl(id)]));
  elements.btnText.textContent='분석하기';
  const document = {
    getElementById: id => elements[id],
    createElement: tag => makeEl(tag),
  };
  const context = {
    document, fetch: fetchImpl, console,
    AbortController, setTimeout, clearTimeout,
  };
  vm.createContext(context);
  vm.runInContext(script, context);
  return {elements, context};
}

async function run() {
  let pass=0;
  // 1 blank input
  {
    const {elements} = setup(async()=>{ throw new Error('should not call'); });
    elements.novelInput.value='   ';
    await elements.analyzeBtn.trigger('click');
    if (!elements.errorBox.textContent.includes('필수값') || !elements.novelInput.focused) throw new Error('blank input failed');
    pass++;
  }
  // 2 success rendering: review tags + sources
  {
    const payload = {
      identified_title:'테스트작', original_title:'原題', author:'작가', origin:'중국', confidence:'높음',
      genre_tags:['#판타지'], atmosphere_tags:['#느린초반','#후반사이다'], translation_tags:['#번역평가혼재'],
      story_arc_map:'성장 전개', charm_points:'리뷰에서 세계관 호평', warning_elements:'초반 속도 호불호', evidence_note:'독자 리뷰 기반',
      sources:[{title:'리뷰1',url:'https://example.com/r1'}], search_queries:['테스트작 리뷰'], grounded:true,
      google_search_entry_point:'<div>Google Search</div>'
    };
    const {elements} = setup(async()=>({ok:true,status:200,json:async()=>payload}));
    elements.novelInput.value='테스트작';
    await elements.analyzeBtn.trigger('click');
    if (elements.resultContainer.classList.contains('hidden')) throw new Error('result hidden');
    if (elements.tagsContainer.children.length !== 4) throw new Error('tag count');
    if (elements.sourcesContainer.children.length !== 1) throw new Error('source count');
    if (elements.resCharm.textContent !== '리뷰에서 세계관 호평') throw new Error('review charm');
    if (elements.btnText.textContent !== '분석하기' || elements.analyzeBtn.disabled) throw new Error('loading reset');
    pass++;
  }
  // 3 server 422 error rendering
  {
    const {elements} = setup(async()=>({ok:false,status:422,json:async()=>({detail:'Google Search 근거 부족'})}));
    elements.novelInput.value='모호한 작품';
    await elements.analyzeBtn.trigger('click');
    if (!elements.errorBox.textContent.includes('Google Search 근거 부족')) throw new Error('422 error');
    pass++;
  }
  // 4 malformed successful JSON rejected
  {
    const {elements} = setup(async()=>({ok:true,status:200,json:async()=>({identified_title:'x'})}));
    elements.novelInput.value='x';
    await elements.analyzeBtn.trigger('click');
    if (!elements.errorBox.textContent.includes('서버 응답 형식이 올바르지 않습니다')) throw new Error('shape validation');
    pass++;
  }
  // 5 non-json rejected
  {
    const {elements} = setup(async()=>({ok:true,status:200,json:async()=>{throw new Error('bad json')}}));
    elements.novelInput.value='x';
    await elements.analyzeBtn.trigger('click');
    if (!elements.errorBox.textContent.includes('JSON이 아닌 응답')) throw new Error('non-json');
    pass++;
  }
  console.log(`frontend scenarios: ${pass}/5 PASS`);
}
run().catch(e=>{console.error(e);process.exit(1)});

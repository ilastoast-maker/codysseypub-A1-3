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
  const ids = ['novelInput','analyzeBtn','btnText','loadingSpinner','errorBox','resultContainer',
    'identifiedTitle','confidenceBadge','identityMeta','summaryTags','infoBar','resStory','resCharm',
    'similarSection','similarList','checklistDetails','checklistSummary','checklistContainer','googleSearchEntryPoint'];
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
  // 2 success rendering: summary keywords, spoiler lock, no source list
  {
    const item = (key,label,category,status,spoiler=false,note='') => ({key,label,category,status,note,spoiler});
    const payload = {
      identified_title:'테스트작', original_title:'原題', author:'작가', origin:'중국', confidence:'높음',
      genre_tags:['#판타지','#회귀'], serial_status:'완결', original_length:'1,200화',
      korean_releases:[{platform:'카카오페이지',note:'800화 연재 중'}],
      entry_point:'초반 30화가 느리다는 평', story_opening:'도입부 소개', charm_points:'리뷰에서 세계관 호평',
      similar_works:[{title:'비교작',reason:'세계관이 비슷하다는 평'}],
      checklist:[
        item('harem','하렘','관계·로맨스','언급됨',false,'하렘 언급'),
        item('lead_swap','남주·여주 교체','관계·로맨스','언급됨',true,'스포'),
        item('frustrating','고구마 구간','주인공','언급없음'),
        item('overpowered','먼치킨','주인공','언급됨'),
        item('sad_ending','새드엔딩','전개·결말','언급됨',true,'슬픈 결말'),
        item('gore','고어·잔혹 묘사','묘사 수위','확인불가'),
      ],
      google_search_entry_point:'<div>Google Search</div>'
    };
    const {elements} = setup(async()=>({ok:true,status:200,json:async()=>payload}));
    elements.novelInput.value='테스트작';
    await elements.analyzeBtn.trigger('click');
    if (elements.resultContainer.classList.contains('hidden')) throw new Error('result hidden');
    const chips = elements.summaryTags.children.map(c=>c.textContent);
    const expected = ['#판타지','#회귀','하렘','먼치킨','완결','카카오페이지'];
    if (JSON.stringify(chips) !== JSON.stringify(expected)) throw new Error('summary chips: '+JSON.stringify(chips));
    if (!elements.infoBar.textContent.includes('원작 1,200화') || !elements.infoBar.textContent.includes('초반 30화')) throw new Error('info bar');
    if (elements.checklistSummary.textContent.indexOf('언급 2건') < 0) throw new Error('count must exclude spoilers: '+elements.checklistSummary.textContent);
    // 스포일러 항목은 클릭 전 상태가 보이면 안 된다
    const rows = elements.checklistContainer.children.flatMap(block=>block.children[1].children);
    const sadRow = rows.find(r=>r.children[0].textContent.includes('새드엔딩'));
    const sadChip = sadRow.children[0];
    if (!sadChip.textContent.includes('🔒') || sadChip.textContent.includes('●')) throw new Error('spoiler visible before click');
    if (sadRow.children.some(c=>c.textContent === '슬픈 결말')) throw new Error('spoiler note visible before click');
    sadChip.trigger('click');
    if (!sadRow.children.some(c=>c.textContent === '● 새드엔딩')) throw new Error('spoiler reveal');
    if (!sadRow.children.some(c=>c.textContent === '슬픈 결말')) throw new Error('spoiler note after reveal');
    // 근거 메모는 칩 뒤에 붙는다
    const haremRow = rows.find(r=>r.children[0].textContent === '● 하렘');
    if (!haremRow || haremRow.children[1].textContent !== '하렘 언급') throw new Error('note order');
    if (elements.resCharm.textContent !== '리뷰에서 세계관 호평') throw new Error('review charm');
    if (elements.similarSection.classList.contains('hidden')) throw new Error('similar hidden');
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

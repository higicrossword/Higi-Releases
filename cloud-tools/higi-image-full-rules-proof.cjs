const fs=require('fs');
const {initializeTestEnvironment,assertSucceeds,assertFails}=require('@firebase/rules-unit-testing');
const {ref,set,update,get}=require('firebase/database');
const p=process.env.RULES_JSON;
if(!p)throw new Error('RULES_JSON missing');
const root=JSON.parse(fs.readFileSync(p,'utf8'));
const test='demo-higi-image-rules-scoped';
const u='https://firebasestorage.googleapis.com/v0/b/higi-8b169.firebasestorage.app/o/higi%2Fcanonical-sources%2Fv1%2F'+
'1'.repeat(64)+'%2F'+'2'.repeat(64)+'.png?alt=media&token=abc-123';
const old='https://firebasestorage.googleapis.com/v0/b/higi-8b169.firebasestorage.app/o/higi%2Fcanonical-sources%2Fv1%2F'+
'1'.repeat(64)+'%2F'+'3'.repeat(64)+'.png?alt=media&token=old-123';
const now=Date.now();
const base={schema:1,parserSchema:2,issueKey:'HAFUCH_DEMO',title:'Demo',
 rows:13,cols:13,blocked:'0'.repeat(169),gridSignature:'grid-13x13-fixed',
 sourceThreadUrl:'https://groups.google.com/g/example',sourceImageUrl:old,
 clues:{H_1:'original clue',V_1:'vertical clue'},answers:{H_1:'answer'},
 clueRegions:{H_1:'crop'},clueRegionLines:{H_1:'row'},
 clueApprovals:{H_1:true},clueRegionsRevision:3,
 revision:3,createdAt:now-5000,updatedAt:now-4000,createdBy:'creator',
 lastEditedBy:'creator',lastEditedByName:'creator'};
function patch(){return {sourceImageUrl:u,revision:4,updatedAt:Date.now(),lastEditedBy:'admin-user',
 lastEditedByName:'Admin',clueRegions:null,clueRegionLines:null,
 clueRegionEvidence:null,clueRegionEdits:null,clueApprovals:null,clueRegionsRevision:4}}
(async()=>{
 const env=await initializeTestEnvironment({projectId:test,database:{rules:JSON.stringify(root)}});
 const admin=env.authenticatedContext('admin-user').database();
 const user=env.authenticatedContext('other').database();
 let passed=0;
 async function reset(){await env.clearDatabase();await env.withSecurityRulesDisabled(async x=>{
  await set(ref(x.database(),'adminUsers/admin-user'),{role:'admin',addedBy:'creator',addedAt:now-5000});
  await set(ref(x.database(),'canonicalPuzzles/P1'),base);
 });}
 async function t(name,fn){await reset();await fn();console.log('PASS',name);passed++}
 try{
  await t('image update admin, content stable',async()=>{await assertSucceeds(update(ref(admin,'canonicalPuzzles/P1'),patch()));
   const x=(await get(ref(admin,'canonicalPuzzles/P1'))).val();
   if(x.clues.H_1!==base.clues.H_1||x.answers.H_1!==base.answers.H_1||x.rows!==13||x.clueRegions)throw Error('Unexpected content change');
  });
  await t('regular user denied',()=>assertFails(update(ref(user,'canonicalPuzzles/P1'),patch())));
  await t('parent write cannot smuggle changed clues',()=>assertFails(set(ref(admin,'canonicalPuzzles/P1'),{...base,...patch(),clues:{H_1:'FORGED'}})));
  await t('multipath image and clue edit denied',()=>assertFails(update(ref(admin,'canonicalPuzzles/P1'),{...patch(),'clues/H_1':'FORGED'})));
  await t('missing revision denied',()=>{let x=patch();delete x.revision;return assertFails(update(ref(admin,'canonicalPuzzles/P1'),x))});
  await t('wrong revision denied',()=>assertFails(update(ref(admin,'canonicalPuzzles/P1'),{...patch(),revision:5})));
  await t('forged external image denied',()=>assertFails(update(ref(admin,'canonicalPuzzles/P1'),{...patch(),sourceImageUrl:'https://example.com/fake.png'})));
  await t('retaining stale crop denied',()=>{let x=patch();delete x.clueRegions;return assertFails(update(ref(admin,'canonicalPuzzles/P1'),x))});
  await t('grid smuggling denied',()=>assertFails(update(ref(admin,'canonicalPuzzles/P1'),{...patch(),rows:12})));
  console.log('PASSED',passed,'scoped tests with full baseline rules');
 }finally{await env.cleanup()}
})().catch(x=>{console.error('FAIL',x);process.exit(1)});

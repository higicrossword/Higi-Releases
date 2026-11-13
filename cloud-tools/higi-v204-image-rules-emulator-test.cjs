const fs=require('fs');
const {initializeTestEnvironment,assertSucceeds,assertFails}=require('@firebase/rules-unit-testing');
const {ref,set}=require('firebase/database');
const PROJECT='demo-higi-image-rule-audit';
const oldUrl='https://firebasestorage.googleapis.com/v0/b/demo-higi-8b169/o/higi%2Fcanonical-sources%2Fv1%2F111.png?alt=media&token=old';
const newUrl='https://firebasestorage.googleapis.com/v0/b/demo-higi-8b169/o/higi%2Fcanonical-sources%2Fv1%2F222.png?alt=media&token=new';
function initial(){
  return {schema:1,parserSchema:2,issueKey:'HAFUCH_DEMO',title:'Demo',rows:13,cols:13,
    blocked:'0'.repeat(169),gridSignature:'grid-13x13-fixed',sourceThreadUrl:'https://groups.google.com/example',
    sourceImageUrl:oldUrl,clues:{H_1:'clue A',V_1:'clue B'},answers:{H_1:'AAA'},
    answerEdits:{H_1:{text:'AAA',by:'u1',name:'a',at:100}},
    clueRegions:{H_1:'box-1'},clueRegionLines:{H_1:'line-1'},clueApprovals:{H_1:true},
    clueRegionsRevision:3,revision:3,createdAt:100,updatedAt:101,createdBy:'original',
    lastEditedBy:'original',lastEditedByName:'original'};
}
function next(v=initial()){
 const n=JSON.parse(JSON.stringify(v));
 n.sourceImageUrl=newUrl;n.revision=v.revision+1;n.clueRegionsRevision=n.revision;
 n.updatedAt=200;n.lastEditedBy='test-admin';n.lastEditedByName='Admin';
 delete n.clueRegions;delete n.clueRegionLines;delete n.clueRegionEvidence;
 delete n.clueRegionEdits;delete n.clueApprovals;return n;
}
(async()=>{
 const env=await initializeTestEnvironment({projectId:PROJECT,
   database:{rules:fs.readFileSync(process.env.RULES_JSON,'utf8')}});
 let count=0;
 const admin=()=>env.authenticatedContext('test-admin').database();
 const user=()=>env.authenticatedContext('regular-user').database();
 const guest=()=>env.unauthenticatedContext().database();
 async function reset(){
   await env.clearDatabase();
   await env.withSecurityRulesDisabled(async ctx=>{
     await set(ref(ctx.database(),'adminUsers/test-admin'),{role:'admin'});
     await set(ref(ctx.database(),'canonicalPuzzles/test-puzzle'),initial());
   });
 }
 async function check(name,promise,allowed){
   if(allowed) await assertSucceeds(promise);
   else await assertFails(promise);
   console.log('PASS',name);count++;
 }
 try{
   await reset(); await check('admin image only',set(ref(admin(),'canonicalPuzzles/test-puzzle'),next()),true);
   await reset(); await check('regular user cannot replace',set(ref(user(),'canonicalPuzzles/test-puzzle'),next()),false);
   await reset(); await check('anonymous cannot replace',set(ref(guest(),'canonicalPuzzles/test-puzzle'),next()),false);
   await reset();const evil=next();evil.rows=12;
   await check('image with grid change denied',set(ref(admin(),'canonicalPuzzles/test-puzzle'),evil),false);
   await reset();const title=next();title.title='different';
   await check('image with changed title denied',set(ref(admin(),'canonicalPuzzles/test-puzzle'),title),false);
   await reset();const badUrl=next();badUrl.sourceImageUrl='https://example.com/forged.png';
   await check('non-managed image URL denied',set(ref(admin(),'canonicalPuzzles/test-puzzle'),badUrl),false);
   await reset();const retained=next();retained.clueRegions={H_1:'stale'};
   await check('retaining stale geometry denied',set(ref(admin(),'canonicalPuzzles/test-puzzle'),retained),false);
   await reset();const generic=initial();generic.clues.H_1='new text';generic.revision++;
   generic.updatedAt=200;generic.lastEditedBy='regular-user';
   await check('existing ordinary clue edit remains allowed',set(ref(user(),'canonicalPuzzles/test-puzzle'),generic),true);
   await reset();const malformed=next();malformed.issueKey='tampered';
   await check('image + changed issue key denied',set(ref(admin(),'canonicalPuzzles/test-puzzle'),malformed),false);
   console.log('EMULATOR PASSED',count,'security rule checks');
 }finally{await env.cleanup();}
})().catch(e=>{console.error('EMULATOR FAILED',e);process.exit(1)});

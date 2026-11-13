const fs=require('fs');
const {initializeTestEnvironment,assertSucceeds,assertFails}=require('@firebase/rules-unit-testing');
const {ref,set,update,get}=require('firebase/database');
const rules=JSON.stringify({rules:{puzzles:{"$key":{
 ".read":"auth != null",
 ".write":false,
 sourceImageUrl:{
  ".write":"auth != null && auth.uid === 'admin' && data.exists() && newData.isString() && newData.val().beginsWith('https://firebasestorage.googleapis.com/') && newData.parent().child('revision').val() === data.parent().child('revision').val()+1 && newData.val() !== data.val()",
  ".validate":"newData.isString() && newData.val().length < 2000"
 },
 revision:{
  ".write":"auth != null && auth.uid === 'admin' && data.parent().child('sourceImageUrl').val() !== newData.parent().child('sourceImageUrl').val() && newData.val() === data.val()+1",
  ".validate":"newData.isNumber() && newData.val() > 0"
 },
 clueRegions:{
  ".write":"auth != null && auth.uid === 'admin' && !newData.exists() && data.parent().child('sourceImageUrl').val() !== newData.parent().child('sourceImageUrl').val() && newData.parent().child('revision').val() === data.parent().child('revision').val()+1"
 },
 updatedAt:{
  ".write":"auth != null && auth.uid === 'admin' && data.parent().child('sourceImageUrl').val() !== newData.parent().child('sourceImageUrl').val() && newData.parent().child('revision').val() === data.parent().child('revision').val()+1"
 }
}}}});
(async()=>{
  const testEnv=await initializeTestEnvironment({projectId:'demo-higi-child-rules-204',database:{rules}});
  const admin=testEnv.authenticatedContext('admin').database();
  const user=testEnv.authenticatedContext('user').database();
  const base={sourceImageUrl:'https://firebasestorage.googleapis.com/old.png',revision:1,updatedAt:100,clues:{H_1:'Original clue'},answers:{H_1:'answer'},clueRegions:{H_1:'crop1'}};
  async function reset(){
    await testEnv.clearDatabase();
    await testEnv.withSecurityRulesDisabled(ctx=>set(ref(ctx.database(),'puzzles/p1'),base));
  }
  const pref='puzzles/p1';
  const newUrl='https://firebasestorage.googleapis.com/new.png';
  let passed=0;
  async function run(name,fn){await reset();await fn();passed++;console.log('PASS',name)}
  try {
    await run('admin atomic child multipath',async()=>{
      await assertSucceeds(update(ref(admin,pref),{sourceImageUrl:newUrl,revision:2,updatedAt:200,clueRegions:null}));
      const snapshot=(await get(ref(admin,pref))).val();
      if(snapshot.clues.H_1!=='Original clue'||snapshot.answers.H_1!=='answer'||snapshot.revision!==2||snapshot.clueRegions)throw new Error('Unexpected data modification');
    });
    await run('regular user update denied',()=>assertFails(update(ref(user,pref),{sourceImageUrl:newUrl,revision:2})));
    await run('admin parent set denied',()=>assertFails(set(ref(admin,pref),{...base,sourceImageUrl:newUrl,revision:2})));
    await run('admin update including clues denied',()=>assertFails(update(ref(admin,pref),{sourceImageUrl:newUrl,revision:2,clues:{H_1:'MALICIOUS'}})));
    await run('admin image only denied missing revision',()=>assertFails(update(ref(admin,pref),{sourceImageUrl:newUrl})));
    await run('admin revision only denied',()=>assertFails(update(ref(admin,pref),{revision:2})));
    console.log('EMULATOR COMPLETE',passed,'checks');
  }finally{await testEnv.cleanup()}
})().catch(e=>{console.error(e);process.exit(1)})

const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const section = (start, end) => html.slice(html.indexOf(start), html.indexOf(end));
const norm = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toUpperCase();
const context = {mcNormLabel:norm, mcCourseAliases:value=>[value]};
vm.createContext(context);
vm.runInContext(section('function mcSyllabusSheetInfo', 'function mcMonthNumber'), context);

// Each cell is one academic block, including its multiline description.
const rows = [
  ['PERIODO', 'CODIGO DE SEMANA', 'Fecha', 'Bloque semanal', 'GEOMETRÍA Y MEDIDA', 'Simulacros', 'OBSERVACIONES'],
  ['', 'SE07', '12-oct', 'A', 'Relaciones Métricas en el Triángulo Rectángulo\n(Teorema de los catetos, la altura y del producto de catetos; T. Pitágoras; cálculo de segmentos proyectados)', 'S07', ''],
  ['', '', '', 'B', 'Identidades Trigonométricas de Ángulos Compuestos\n(Suma y Diferencia, identidades auxiliares y simplificaciones algebraicas)', '', ''],
  ['', '', '', 'C', '', '', ''],
  ['', 'SE08', '19-oct', 'A', 'Tema uno', 'S08', 'Aviso de la semana'],
  ['', '', '', 'B', 'Tema dos', '', ''],
  ['', '', '', 'C', 'Tema tres', '', ''],
  ['', '', '', 'D', 'Tema cuatro', '', '']
];
const weeks = JSON.parse(JSON.stringify(context.mcParseSyllabusRows(rows, 'GEOMETRÍA Y MEDIDA')));
assert.equal(weeks[0].topics.length, 2);
assert.match(weeks[0].topics[0], /cálculo de segmentos proyectados\)$/);
assert.match(weeks[0].topics[1], /^Identidades Trigonométricas de Ángulos Compuestos/);
assert.equal(weeks[1].topics.length, 4, 'A fourth block must not be discarded');
assert.deepEqual(weeks[1].notes, ['Aviso de la semana']);
assert.equal(context.mcParseSyllabusCsv(context.mcRowsToCsv(rows), 'GEOMETRÍA Y MEDIDA')[0].topics.length, 2);
const genericRows = rows.map(row=>row.slice(1));
assert.equal(context.mcParseSyllabusRows(genericRows, 'GEOMETRÍA Y MEDIDA')[0].topics.length, 2);

const sheet = 'https://docs.google.com/spreadsheets/d/example/edit';
assert.ok(!context.mcSyllabusCsvUrl(sheet).includes('gid='));
assert.ok(context.mcSyllabusCsvUrl(sheet + '?gid=11988891').endsWith('&gid=11988891'));
assert.ok(context.mcSyllabusCsvUrl(sheet + '?gid=0').endsWith('&gid=0'));

// Full blocks survive alignment and holiday handling, without a three-topic cap.
Object.assign(context, {
  mcDateKey:d=>d ? `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}` : '',
  mcParseSheetDate:value=>value ? new Date(2026, 9, Number(value.split('-')[0])) : null,
  mcHolidaysFromSyllabusNotes:()=>new Map(),
  mcScheduleDaysForEscolaresMateriales:()=>[1, 3],
  pgxAddDays:(d,n)=>new Date(d.getFullYear(),d.getMonth(),d.getDate()+n),
  mcClassDatesFromBaseWeek:({baseDate})=>[baseDate, new Date(baseDate.getTime()+2*86400000)],
  mcSyllabusNotesForWeek:notes=>notes
});
vm.runInContext(section('function mcSyllabusWeekCapacity', 'function mcManualSyllabusAligned'), context);
const aligned = context.mcAlignSyllabusTopics({weeks,codes:['SE07','SE08'],first:1,last:2,pStart:new Date(2026,9,12),local:'EDITOR',course:'GEOMETRÍA Y MEDIDA',programType:'PUCP'});
assert.equal(aligned[0].topics.length, 2);
assert.match(aligned[0].topics[1], /^Identidades Trigonométricas/);
assert.equal(aligned[1].topics.length, 4);

// A cached read expires; simultaneous reads share the same pending request.
let now = 1000;
let reads = 0;
const loaderContext = {
  ...context,
  Date:class extends Date {static now(){return now;}},
  MC_ARS_SYLLABUS_CACHE:new Map(), MC_SYLLABUS_CACHE_MS:60000,
  mcLoadSyllabusGvizRows:async()=>{reads++; return rows;}
};
vm.createContext(loaderContext);
vm.runInContext(section('async function mcLoadSyllabusData', 'async function mcHydrateMaterialesSyllabus'), loaderContext);

(async()=>{
  await Promise.all([loaderContext.mcLoadSyllabusData(sheet,'GEO'),loaderContext.mcLoadSyllabusData(sheet,'GEO')]);
  assert.equal(reads, 1);
  now += 59000;
  await loaderContext.mcLoadSyllabusData(sheet,'GEO');
  assert.equal(reads, 1);
  now += 2000;
  await loaderContext.mcLoadSyllabusData(sheet,'GEO');
  assert.equal(reads, 2, 'Sheet contents must refresh after cache expiry');

  // A slow response for the previous course cannot overwrite the current one.
  const deferred = {};
  const cell = {isConnected:true, innerHTML:''};
  const status = {textContent:''};
  const hydrateContext = {
    MC_SYLLABUS_REQUEST_ID:0,
    MC_ACTIVE_SYLLABUS_CONTEXT:null,
    MC_ACTIVE_SYLLABUS_ITEMS:[],
    document:{querySelectorAll:()=>[cell], getElementById:id=>id==='mcSyllabusStatus' ? status : null},
    mcScheduleDaysForEscolaresMateriales:()=>[1],
    mcManualSyllabusAligned:()=>null,
    mcLoadSyllabusData:url=>new Promise(resolve=>{deferred[url]=resolve;}),
    mcAlignSyllabusTopics:({weeks})=>weeks,
    mcSyllabusCellHtml:item=>item.topics.join(' | '),
    mcBindSyllabusButtons:()=>{},
    console
  };
  vm.createContext(hydrateContext);
  vm.runInContext(section('async function mcHydrateMaterialesSyllabus', 'async function mcRefreshActiveSyllabus'),hydrateContext);
  const params = {pid:'program', codes:['SE07'],first:1,last:1};
  const previous = hydrateContext.mcHydrateMaterialesSyllabus({...params,cid:'GEO',url:'previous'});
  const current = hydrateContext.mcHydrateMaterialesSyllabus({...params,cid:'ALG',url:'current'});
  deferred.current([{topics:['Current course']}]);
  await current;
  deferred.previous([{topics:['Previous course']}]);
  await previous;
  assert.equal(cell.innerHTML,'Current course');
  assert.equal(hydrateContext.MC_ACTIVE_SYLLABUS_ITEMS[0].topics[0],'Current course');
  console.log('Sílabos: bloques, CSV, pestañas, alineación, caché y respuestas tardías: OK');
})().catch(error=>{console.error(error); process.exitCode=1;});

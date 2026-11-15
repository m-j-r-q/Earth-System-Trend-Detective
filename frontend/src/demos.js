// Guided demos. Text never states a result: numbers come from the live data through {{placeholders}}.
//   {{prev.x}} refers to the previous step's values, which lets a step compare before and after a change.
// `set` changes the app state when a step opens: tab ('trends' | 'vars' | 'regions'), start/end years.

export const DEMOS = [
  {
    id: 'sahel',
    title: 'Does the answer depend on when you start?',
    blurb: 'Sahel rainfall after a famous drought. Change the start year and watch the verdict move.',
    region: 'sahel',
    variables: ['PRECTOT'],
    steps: [
      {
        title: 'A place with a famous story',
        target: 'tour-region',
        set: { tab: 'trends', start: null, end: null },
        text: 'The Sahel is the semi-arid belt south of the Sahara. It suffered one of the worst multi-year droughts on record in the 1970s and 80s, and rainfall has partly recovered since. That makes it a good test of a question trend detectives face constantly: does the answer depend on when you start looking?',
      },
      {
        title: 'What we measure',
        target: 'tour-variables',
        set: { tab: 'trends', start: null, end: null },
        text: 'This is precipitation from the MERRA-2 model, which begins in 1980. A long record helps, because it takes many years to tell a real trend from ordinary wet and dry spells. Press the i next to any variable to read what it means.',
      },
      {
        title: 'Reading the chart',
        target: 'tour-chart',
        set: { tab: 'trends', start: null, end: null },
        text: 'The pale line is each month with the seasons removed. The dark line is a 12-month average and the dashed line is the fitted trend. Notice how far the dark line wanders on its own. That wandering is natural variability, and any real trend has to stand out against it.',
      },
      {
        title: 'The verdict',
        target: 'tour-stats',
        set: { tab: 'trends', start: null, end: null },
        text: 'From {{start}} to {{end}}, {{variable}} in the {{region}} is {{direction}} at {{slope}} {{unit}} per decade, with a 95% range of {{ci}} and {{p}}. {{verdict}}',
      },
      {
        title: 'Move the start year',
        target: 'tour-dates',
        set: { tab: 'trends', start: 2000, end: null },
        text: 'The window now begins in {{start}}. The trend is {{slope}} {{unit}} per decade ({{p}}). Over the full record it was {{prev.slope}} ({{prev.p}}). Compare the direction, the size and the verdict. If they differ, the result depends on the window, and a careful analyst reports both.',
      },
      {
        title: 'Now investigate',
        target: null,
        set: { tab: 'trends', start: 2000, end: null },
        text: 'Try the other tabs: compare several variables in this region, or compare one variable across regions. Use the time window to test whether a trend you find holds up.',
      },
    ],
  },
  {
    id: 'indus',
    title: 'Warming in the water towers',
    blurb: 'Upper Indus and Karakoram: temperature, rain and soil moisture, and whether they move together.',
    region: 'upper_indus',
    variables: ['T2M', 'PRECTOT', 'SOILM'],
    steps: [
      {
        title: 'Where Pakistan’s water starts',
        target: 'tour-region',
        set: { tab: 'trends', start: null, end: null },
        text: 'Glaciers and snow in the Upper Indus basin feed the Indus River, which supplies water to hundreds of millions of people. The Karakoram is known for glaciers that have behaved differently from most others, so local data matters more here than global headlines.',
      },
      {
        title: 'Temperature first',
        target: 'tour-stats',
        set: { tab: 'trends', start: null, end: null },
        text: '{{variable}} is {{direction}} at {{slope}} {{unit}} per decade (95% range {{ci}}, {{p}}). {{verdict}}',
      },
      {
        title: 'Three measurements, one chart',
        target: 'tour-compare',
        set: { tab: 'vars', start: null, end: null },
        text: 'Temperature, precipitation and soil moisture now share one axis. Their trends per decade: {{summary}}.',
      },
      {
        title: 'Do they move together?',
        target: 'tour-compare',
        set: { tab: 'vars', start: null, end: null },
        text: 'The strongest link between the month-by-month anomalies is {{link}}. A link suggests both respond to the same weather, but it does not show that one causes the other.',
      },
      {
        title: 'Your turn',
        target: null,
        set: { tab: 'vars', start: null, end: null },
        text: 'Switch variables on and off in the left panel, or narrow the time window, and see which conclusions survive.',
      },
    ],
  },
  {
    id: 'opposite',
    title: 'Same planet, different directions',
    blurb: 'Precipitation across four regions. Do all the trends point the same way?',
    region: 'sahel',
    variables: ['PRECTOT'],
    cmpVar: 'PRECTOT',
    cmpRegions: ['sahel', 'amazon_arc', 'central_valley', 'indo_gangetic'],
    steps: [
      {
        title: 'One measurement, four places',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Rainfall depends on winds, ocean temperatures and local landscape, so a warming planet need not push every region the same way. Here is the same measurement in four regions at once.',
      },
      {
        title: 'Read the dots',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Trends per decade: {{summary}}. Filled dots are significant; hollow dots are not. A bar that crosses the zero line means that region could be showing no change at all.',
      },
      {
        title: 'Opposite directions?',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Do any two regions move in opposite directions, both significantly? {{opposite}}',
      },
      {
        title: 'Why this matters',
        target: null,
        set: { tab: 'regions', start: null, end: null },
        text: 'A global average can hide opposite regional trends. That is why this tool analyzes one region at a time.',
      },
    ],
  },
  {
    id: 'arctic',
    title: 'Is the Arctic really warming faster?',
    blurb: 'Compare temperature trends in the Barents-Kara Arctic with three other regions.',
    region: 'arctic_barents',
    variables: ['T2M'],
    cmpVar: 'T2M',
    cmpRegions: ['arctic_barents', 'upper_indus', 'sahel', 'amazon_arc'],
    steps: [
      {
        title: 'A claim worth checking',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Scientists have long expected the Arctic to warm faster than the rest of the planet, partly because melting sea ice exposes darker ocean that absorbs more heat. Does this data agree?',
      },
      {
        title: 'Warming rates compared',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Temperature trends per decade: {{summary}}.',
      },
      {
        title: 'Are the regions really different?',
        target: 'tour-compare',
        set: { tab: 'regions', start: null, end: null },
        text: 'Look at the bars. If two bars do not overlap, the regions differ by more than the uncertainty. If they overlap, the data cannot separate them. Try shortening the time window to see how the bars grow.',
      },
    ],
  },
  {
    id: 'aral',
    title: 'The lake that vanished',
    blurb: 'The Aral Sea basin: evaporation, temperature and soil moisture around a drying lake.',
    region: 'aral_sea',
    variables: ['EVAP', 'T2M', 'SOILM', 'PRECTOT'],
    steps: [
      {
        title: 'What happened here',
        target: 'tour-region',
        set: { tab: 'trends', start: null, end: null },
        text: 'The Aral Sea was once the fourth-largest lake in the world. From the 1960s the rivers feeding it were diverted to irrigate crops, and it shrank dramatically. This box covers the lake and its surroundings.',
      },
      {
        title: 'Evaporation',
        target: 'tour-stats',
        set: { tab: 'trends', start: null, end: null },
        text: '{{variable}} is {{direction}} at {{slope}} {{unit}} per decade ({{p}}). {{verdict}} When a lake dries, open water is replaced by land, so this measurement is worth reading alongside temperature and soil moisture.',
      },
      {
        title: 'Several measurements together',
        target: 'tour-compare',
        set: { tab: 'vars', start: null, end: null },
        text: 'Trends per decade: {{summary}}.',
      },
      {
        title: 'Your turn',
        target: null,
        set: { tab: 'vars', start: null, end: null },
        text: 'Open the definitions with the i buttons, change the window, and decide which of these trends you trust.',
      },
    ],
  },
]

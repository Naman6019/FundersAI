const chatUrl = 'http://127.0.0.1:3000/api/chat';
const query = 'Compare ICICI Multi Asset and Parag Flexi Cap';

async function run() {
    console.log('Sending chat request...');
    const chatRes = await fetch(chatUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, asset_type: 'auto', research_depth: 'standard', comparison_view_mode: 'canvas' })
    });
    
    if (!chatRes.ok) {
        console.error('Chat error:', await chatRes.text());
        return;
    }
    
    const chatData = await chatRes.json();
    console.log('Chat system_action:', JSON.stringify(chatData.system_action, null, 2));
    
    const ids = chatData.system_action?.ids || [];
    console.log('Resolved IDs:', ids);
    
    for (const id of ids) {
        console.log(`\nFetching data for scheme ${id}...`);
        const mfRes = await fetch(`http://127.0.0.1:3000/api/mf/${id}`);
        if (!mfRes.ok) {
            console.error(`MF API error for ${id}:`, await mfRes.text());
            continue;
        }
        
        const mfData = await mfRes.json();
        const details = mfData.details || {};
        console.log(`[${id}] Name:`, details.scheme_name || details.name);
        
        console.log(`[${id}] historyCoverage exists:`, !!mfData.historyCoverage);
        if (mfData.historyCoverage) {
            const coverage = mfData.historyCoverage;
            const supports = coverage.supports || {};
            console.log(`[${id}] Supports 1Y: ${supports['1Y']}, 3Y: ${supports['3Y']}, 5Y: ${supports['5Y']}`);
            console.log(`[${id}] Date range: ${coverage.first_nav_date || coverage.firstNavDate} to ${coverage.last_nav_date || coverage.lastNavDate}`);
            console.log(`[${id}] Total points available: ${coverage.history_points || coverage.historyPoints}`);
        }
        
        console.log(`[${id}] historical_nav/fullData exists:`, !!mfData.fullData);
        const dataArr = mfData.fullData || mfData.chartData;
        if (dataArr) {
            console.log(`[${id}] array row count:`, dataArr.length);
        }
    }
}
run();

const fs = require('fs');

// Read the HTML file
const html = fs.readFileSync('C:\\Users\\DAVID\\Documents\\GitHub\\Rockstar-Beta\\company_system\\templates\\task_management\\personal_board_detail.html', 'utf8');
const lines = html.split('\n');

// Extract only script content between <script> and </script> tags. Our script starts at line 776 and ends at 2506 but we can also find the tags.
// Since we know it's the only script at the end, we can extract lines 776-2506 inclusive.

// Extract only script content lines 776-2506, then strip <script> and </script>
const scriptLines = lines.slice(775, 2506); // includes both <script> and </script>
// Remove the first line if it's <script> and last if it's </script>
if (scriptLines[0].trim() === '<script>') scriptLines.shift();
if (scriptLines[scriptLines.length-1].trim() === '</script>') scriptLines.pop();
let jsCode = scriptLines.join('\n');

// Remove Django template tags: {% ... %} and replace {{ ... }} with null for placeholder
jsCode = jsCode.replace(/{%.*?%}/gs, '');  // remove block tags entirely
jsCode = jsCode.replace(/{{.*?}}/gs, 'null'); // replace expression tags with null

// Save for inspection (optional)
fs.writeFileSync('debug_extracted.js', jsCode);

// Save to a .js file
fs.writeFileSync('debug_extracted.js', jsCode);

// Try to compile using Node's vm to get SyntaxError with line number
try {
    const vm = require('vm');
    // Create a context with browser-like globals (minimal)
    const context = {
        document: { createElement: () => ({ innerHTML: '' }), cookie: '' },
        window: {},
        console: console,
        setTimeout: setTimeout,
        clearTimeout: clearTimeout,
        FullCalendar: null,
        Sortable: function() {},
        location: { href: '' }
    };
    vm.createContext(context);
    vm.runInContext(jsCode, context, { filename: 'extracted.js' });
    console.log('No syntax errors detected by vm.runInContext');
} catch (e) {
    if (e instanceof SyntaxError) {
        console.log('SyntaxError:', e.message);
        console.log('Line:', e.lineNumber, 'Column:', e.columnNumber);
    } else {
        console.error('Error:', e);
    }
}

// Also try using new Function to catch syntax errors
try {
    // eslint-disable-next-line no-new-func
    new Function(jsCode);
    console.log('new Function check: no syntax error');
} catch (e) {
    if (e instanceof SyntaxError) {
        console.log('SyntaxError from new Function:', e.message);
        console.log('Line (relative to extracted code):', e.lineNumber);
        // Compute original line: line 1 of extracted code is line 776 of original.
        if (e.lineNumber) {
            console.log('Approx original line:', (e.lineNumber + 775));
        }
    } else {
        console.error('Error:', e);
    }
}

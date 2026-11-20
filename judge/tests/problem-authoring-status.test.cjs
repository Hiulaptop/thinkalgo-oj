const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const script = fs.readFileSync(path.join(__dirname, '../../resources/problem-authoring.js'), 'utf8');
const idle = {revision: 3, data_state: 'READY', operation_state: 'READY', run_state: 'FINISHED',
    result: 'AC', stale_verification: false, can_verify: true, can_publish: true, safe_error: ''};
const working = {...idle, data_state: 'PENDING', operation_state: 'INSTALLING', run_state: null,
    result: null, can_verify: false, can_publish: false};

function page(respond, hidden = false) {
    const timers = new Map();
    const listeners = {};
    const requests = [];
    let timerId = 0;
    const message = {textContent: ''};
    const buttons = {verify: {disabled: false}, publish: {disabled: false}};
    const editor = {dataset: {authoringStatusUrl: '/problem/demo/edit?status=1', authoringRevision: '3'},
        querySelector(selector) {
            if (selector === '[data-authoring-live-status]') return message;
            return buttons[selector.match(/value="(\w+)"/)[1]];
        }};
    const document = {readyState: 'complete', hidden,
        querySelector: () => editor,
        addEventListener: (event, callback) => { listeners[event] = callback; }};
    const window = {setTimeout(callback, delay) {
        const id = ++timerId;
        timers.set(id, {callback, delay});
        return id;
    }, clearTimeout(id) { timers.delete(id); }, addEventListener(event, callback) { listeners[event] = callback; }};
    vm.runInNewContext(script, {document, window, AbortController,
        fetch(url, options) {
            requests.push({url, options});
            return respond(options, requests.length);
        }});
    return {requests, timers, message, buttons, document,
        async settle() { for (let i = 0; i < 12; i++) await Promise.resolve(); },
        async tick(delay) {
            const entry = [...timers].find(([, timer]) => timer.delay === delay);
            assert.ok(entry, 'Expected scheduled delay ' + delay + ', got ' + [...timers.values()].map(t => t.delay));
            timers.delete(entry[0]);
            entry[1].callback();
            await this.settle();
        },
        async visible(value) {
            document.hidden = !value;
            if (listeners.visibilitychange) listeners.visibilitychange();
            await this.settle();
        },
        async close() { if (listeners.pagehide) listeners.pagehide(); await this.settle(); }};
}
const response = state => Promise.resolve({ok: true, headers: {get: () => 'application/json'},
    json: async () => state});

test('idle editor updates capabilities once without endless polling', async () => {
    const p = page(() => response(idle));
    await p.settle();
    assert.equal(p.requests.length, 1);
    assert.equal(p.buttons.publish.disabled, false);
    assert.equal(p.timers.size, 0);
    await p.visible(false);
    await p.visible(true);
    assert.equal(p.requests.length, 1);
});

test('active operation is polled until completion without changing saved revision', async () => {
    const p = page((_, n) => response(n === 1 ? working : {...idle, revision: 4}));
    await p.settle();
    await p.tick(5000);
    assert.equal(p.requests.length, 2);
    assert.equal(p.buttons.verify.disabled, true);
    assert.equal(p.buttons.publish.disabled, true);
    assert.match(p.message.textContent, /Có phiên bản mới/);
    assert.equal(p.timers.size, 0);
});

test('hidden editor waits for visibility before requesting status', async () => {
    const p = page(() => response(working), true);
    await p.settle();
    assert.equal(p.requests.length, 0);
    await p.visible(true);
    assert.equal(p.requests.length, 1);
    await p.visible(false);
    assert.equal(p.timers.size, 0);
    await p.visible(true);
    assert.equal(p.requests.length, 2);
});

test('network and HTTP failures back off and stop after five consecutive failures', async () => {
    const p = page((_, n) => n % 2 ? Promise.reject(new Error('offline')) : Promise.resolve({ok: false}));
    await p.settle();
    for (const delay of [5000, 10000, 20000, 40000]) await p.tick(delay);
    assert.equal(p.requests.length, 5);
    assert.equal(p.timers.size, 0);
    assert.match(p.message.textContent, /Nội dung đang nhập vẫn được giữ nguyên/);
});

test('hung request is aborted and schedules a retry', async () => {
    let signal;
    const p = page(options => new Promise((resolve, reject) => {
        signal = options.signal;
        if (signal) signal.addEventListener('abort', () => reject(new Error('aborted')));
    }));
    await p.settle();
    await p.tick(10000);
    assert.equal(signal.aborted, true);
    assert.equal(p.requests.length, 1);
    assert.ok([...p.timers.values()].some(timer => timer.delay === 5000));
});

test('leaving the page aborts pending work without scheduling retries', async () => {
    let signal;
    const p = page(options => new Promise((resolve, reject) => {
        signal = options.signal;
        if (signal) signal.addEventListener('abort', () => reject(new Error('aborted')));
    }));
    await p.settle();
    await p.close();
    assert.equal(signal.aborted, true);
    assert.equal(p.timers.size, 0);
});

test('a successful response resets failure backoff while a verification is running', async () => {
    const p = page((_, n) => n === 2 ? response({...idle, run_state: 'JUDGING'}) : Promise.reject(new Error('offline')));
    await p.settle();
    await p.tick(5000);
    await p.tick(5000);
    assert.equal(p.requests.length, 3);
    assert.ok([...p.timers.values()].some(timer => timer.delay === 5000));
});

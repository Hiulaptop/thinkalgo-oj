(() => {
    'use strict';
    function startAuthoringStatus() {
        const editor = document.querySelector('[data-authoring-status-url]');
        if (!editor) return;
        const message = editor.querySelector('[data-authoring-live-status]');
        const revision = Number(editor.dataset.authoringRevision);
        let timer;
        let controller;
        let failures = 0;
        let active = true;
        let stopped = false;
        async function refresh() {
            if (stopped || document.hidden || controller || !active) return;
            controller = new AbortController();
            const timeout = window.setTimeout(() => controller?.abort(), 10000);
            let delay = 5000;
            try {
                const response = await fetch(editor.dataset.authoringStatusUrl, {
                    credentials: 'same-origin', cache: 'no-store', headers: {'Accept': 'application/json'},
                    signal: controller.signal,
                });
                if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
                    throw new Error('Invalid status response');
                }
                const state = await response.json();
                failures = 0;
                active = ['PENDING', 'INSTALLING', 'PUBLISHING', 'WAITING'].includes(state.operation_state) ||
                    ['PENDING', 'DISPATCHING', 'JUDGING'].includes(state.run_state);
                const changed = state.revision !== revision;
                const parts = ['Dữ liệu: ' + state.data_state, 'Kiểm chứng: ' + (state.run_state || 'chưa chạy')];
                if (state.result) parts.push(state.result);
                if (state.stale_verification) parts.push('Kết quả thuộc phiên bản cũ');
                if (changed) parts.push('Có phiên bản mới; sao chép phần chưa lưu trước khi tải lại');
                if (state.safe_error) parts.push(state.safe_error);
                message.textContent = parts.join(' · ');
                for (const [action, allowed] of [['verify', state.can_verify], ['publish', state.can_publish]]) {
                    const button = editor.querySelector('button[value="' + action + '"]');
                    if (button) button.disabled = changed || !allowed;
                }
            } catch (_) {
                if (!stopped && !document.hidden) {
                    failures += 1;
                    delay = Math.min(5000 * 2 ** (failures - 1), 60000);
                    if (failures >= 5) stopped = true;
                    message.textContent = 'Không lấy được trạng thái mới. Nội dung đang nhập vẫn được giữ nguyên.';
                }
            } finally {
                window.clearTimeout(timeout);
                controller = null;
                if (!stopped && active && !document.hidden) timer = window.setTimeout(refresh, delay);
            }
        }
        document.addEventListener('visibilitychange', () => {
            window.clearTimeout(timer);
            if (document.hidden) controller?.abort();
            else refresh();
        });
        window.addEventListener('pagehide', () => {
            stopped = true;
            window.clearTimeout(timer);
            controller?.abort();
        });
        refresh();
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startAuthoringStatus);
    else startAuthoringStatus();
})();

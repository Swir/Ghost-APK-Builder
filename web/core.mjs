export const COLORS = Object.freeze(['#8FA0FF','#62E5FF','#44E6A8','#FFD166','#FF8FAB','#C77DFF','#FF9F68','#7AE582','#5CC8FF','#B8C0FF','#F4A261','#E879F9']);
export function cleanNick(value) {
  const nick = String(value ?? '').normalize('NFC').trim();
  if (!nick || [...nick].length > 32 || /[\u0000-\u001f\u007f]/u.test(nick)) throw new Error('inputNick');
  return nick;
}
export function cleanMessage(value) {
  const text = String(value ?? '').trim();
  if (!text || [...text].length > 4000) throw new Error('inputMessage');
  return text;
}
export function cleanBootstraps(value) {
  const lines = [...new Set(String(value ?? '').split(/\r?\n/).map(x => x.trim()).filter(Boolean))];
  if (lines.length > 32 || lines.some(x => x.length > 2048 || !x.startsWith('/') || !x.includes('/p2p/') || /\s/.test(x))) throw new Error('seedInvalid');
  return lines;
}
export function nativeBridge(native = globalThis.__TAURI__) {
  if (!native?.core?.invoke || !native?.event?.listen) return null;
  return {
    invoke: (name, args) => native.core.invoke(name, args),
    listen: (name, handler) => native.event.listen(name, ({ payload }) => handler(payload)),
  };
}
export class ChatController {
  constructor(bridge, notify = () => {}) {
    this.bridge = bridge; this.notify = notify; this.unlisten = []; this.seen = new Set();
    this.session = 0; this.started = false; this.busy = false; this.sending = false;
    this.state = { phase:'offline', nick:'', peerId:'', connectedPeers:0, bootstraps:0, messages:[], logs:[], error:'' };
  }
  emit() { this.notify(this.state); }
  log(message, level = 'info') {
    this.state.logs.push({ text:String(message).slice(0, 2500), level, time:Date.now() });
    this.state.logs = this.state.logs.slice(-80); this.emit();
  }
  async clearListeners() {
    const callbacks = this.unlisten.splice(0);
    await Promise.allSettled(callbacks.map(async fn => fn()));
  }
  status(payload) {
    if (!payload || typeof payload !== 'object') return;
    const count = Number(payload.connected_peers);
    this.state.connectedPeers = Number.isSafeInteger(count) && count >= 0 ? count : 0;
    this.state.bootstraps = Number.isSafeInteger(payload.bootstrap_count) ? Math.max(0,payload.bootstrap_count) : 0;
    this.state.phase = this.state.connectedPeers > 0 && payload.phase === 'online' ? 'online' : 'searching';
    if (typeof payload.detail === 'string') this.log(payload.detail);
    this.emit();
  }
  message(payload) {
    if (!payload || payload.kind !== 'chat' || payload.room !== 'world' || typeof payload.id !== 'string' ||
        !payload.id || payload.id.length > 200 || typeof payload.peer_id !== 'string' ||
        payload.peer_id.length > 200 || typeof payload.nick !== 'string' || payload.nick.length > 128 ||
        typeof payload.text !== 'string' || [...payload.text].length > 4000) return;
    const key = `${payload.peer_id}\0${payload.id}`;
    if (this.seen.has(key)) return;
    this.seen.add(key);
    while (this.seen.size > 1000) this.seen.delete(this.seen.values().next().value);
    const time = Number(payload.timestamp);
    this.state.messages.push({ ...payload, nick_color:COLORS.includes(payload.nick_color) ? payload.nick_color : COLORS[0],
      timestamp:Number.isSafeInteger(time) && time > 0 && time <= 8640000000000000 ? time : Date.now() });
    this.state.messages = this.state.messages.slice(-300); this.emit();
  }
  async connect(nickValue, color, seeds) {
    if (!this.bridge) throw new Error('runtimeMissing');
    if (this.busy || this.started) throw new Error('startOnce');
    const nick = cleanNick(nickValue), bootstraps = cleanBootstraps(seeds);
    this.busy = true; const generation = ++this.session;
    this.state = { ...this.state, phase:'starting', error:'', messages:[], peerId:'', connectedPeers:0 };
    this.seen.clear(); this.emit();
    try {
      await this.clearListeners();
      const bind = async (name, handler) => {
        const stop = await this.bridge.listen(name, payload => {
          if (generation === this.session) handler(payload);
        });
        this.unlisten.push(stop);
      };
      await bind('network-status', p => this.status(p));
      await bind('chat-message', p => this.message(p));
      await bind('network-log', p => this.log(p));
      await bind('network-warning', p => this.log(p, 'warning'));
      await bind('network-error', p => {
        this.state.error = String(p); this.state.phase = 'error'; this.started = false;
        this.state.connectedPeers = 0; this.log(p, 'error');
      });
      await bind('file-offer', p => {
        if (typeof p?.transfer_id !== 'string') return;
        this.bridge.invoke('reject_file', { transferId:p.transfer_id })
          .then(() => this.log('fileRejected'))
          .catch(error => this.log(error, 'warning'));
      });
      const result = await this.bridge.invoke('start_network', {
        nick, nickColor:COLORS.includes(color) ? color : COLORS[0], bootstraps,
      });
      if (!result || typeof result.peer_id !== 'string') throw new Error('Invalid native start response');
      if (generation !== this.session || this.state.phase === 'error') throw new Error(this.state.error || 'Start cancelled');
      this.started = true; this.state.peerId = result.peer_id; this.state.nick = result.nick || nick;
      if (this.state.phase === 'starting') this.state.phase = 'searching';
      await this.bridge.invoke('set_private_messages_enabled', { enabled:false });
      this.emit(); return result;
    } catch (error) {
      try { await this.bridge.invoke('disconnect_network'); } catch (cleanup) { this.log(cleanup, 'warning'); }
      this.started = false; this.state.phase = 'error'; this.state.connectedPeers = 0;
      this.state.error = String(error?.message || error); await this.clearListeners(); this.emit(); throw error;
    } finally { this.busy = false; this.emit(); }
  }
  async disconnect() {
    if (!this.bridge || this.busy) return;
    this.busy = true; this.emit();
    try {
      await this.bridge.invoke('disconnect_network');
      ++this.session; this.started = false; await this.clearListeners(); this.seen.clear();
      this.state = { ...this.state, phase:'offline', peerId:'', connectedPeers:0, messages:[], error:'' };
    } catch (error) {
      this.state.error = String(error?.message || error); this.state.phase = 'error'; throw error;
    } finally { this.busy = false; this.emit(); }
  }
  async send(value) {
    if (!this.bridge || !this.started || this.state.phase !== 'online' || this.state.connectedPeers < 1) throw new Error('notOnline');
    if (this.sending) throw new Error('A message is already being submitted.');
    const text = cleanMessage(value); this.sending = true; this.emit();
    try { await this.bridge.invoke('send_message', { room:'world', text }); }
    finally { this.sending = false; this.emit(); }
  }
  async refresh() {
    if (!this.bridge || !this.started || this.busy) return;
    await this.bridge.invoke('refresh_discovery');
  }
}

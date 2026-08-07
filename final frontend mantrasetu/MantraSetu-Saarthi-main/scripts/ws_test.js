// ws_test.js - simple client to verify backend voice websocket
const WebSocket = require('ws');
const ws = new WebSocket('ws://localhost:8000/ws/voice');
ws.on('open', () => {
  console.log('WebSocket opened');
  ws.send(JSON.stringify({
    type: 'CONNECT',
    conversation_id: 'test_conv',
    payload: { language: 'hi' }
  }));
  console.log('CONNECT sent');
});
ws.on('message', data => {
  const msg = JSON.parse(data);
  console.log('Received:', msg.type, msg.payload);
});
ws.on('error', err => console.error('WS error', err));
ws.on('close', () => console.log('WebSocket closed'));

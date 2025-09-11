const WebSocket = require('ws');

// Explore ASR protocol
const ASR_URL = 'wss://s6rou7ayi3jrzc-3000.proxy.runpod.net/ws/asr';

console.log('🔍 Exploring ASR Protocol...');
console.log(`🔗 Connecting to: ${ASR_URL}`);

const ws = new WebSocket(ASR_URL);

ws.on('open', () => {
  console.log('✅ Connected to ASR service');
  
  // Try different message types commonly used in ASR services
  const testMessages = [
    { type: 'start' },
    { type: 'config', sample_rate: 16000, encoding: 'pcm' },
    { type: 'audio_config', sample_rate: 16000, channels: 1, encoding: 'LINEAR16' },
    { type: 'init', config: { sample_rate: 16000, encoding: 'pcm' } },
    { type: 'begin' },
    { type: 'hello' },
    { type: 'ping' },
    { type: 'status' },
    { type: 'info' }
  ];
  
  let messageIndex = 0;
  
  function sendNextMessage() {
    if (messageIndex < testMessages.length) {
      const message = testMessages[messageIndex];
      console.log(`\n📤 Sending message ${messageIndex + 1}/${testMessages.length}:`, JSON.stringify(message));
      ws.send(JSON.stringify(message));
      messageIndex++;
      
      setTimeout(sendNextMessage, 1000);
    } else {
      console.log('\n🏁 All test messages sent');
      
      // Try sending some dummy audio data
      console.log('\n📤 Testing audio data formats...');
      
      // Test 1: JSON with base64 audio
      setTimeout(() => {
        const audioMessage = {
          type: 'audio',
          data: Buffer.from('dummy audio data').toString('base64')
        };
        console.log('📤 Sending JSON audio message:', JSON.stringify(audioMessage));
        ws.send(JSON.stringify(audioMessage));
      }, 1000);
      
      // Test 2: Binary audio data
      setTimeout(() => {
        console.log('📤 Sending binary audio data...');
        const binaryData = Buffer.from('dummy binary audio data');
        ws.send(binaryData);
      }, 2000);
      
      // Test 3: Audio chunk message
      setTimeout(() => {
        const chunkMessage = {
          type: 'chunk',
          audio: Buffer.from('dummy chunk data').toString('base64')
        };
        console.log('📤 Sending chunk message:', JSON.stringify(chunkMessage));
        ws.send(JSON.stringify(chunkMessage));
      }, 3000);
      
      // Close after testing
      setTimeout(() => {
        console.log('\n🔚 Closing connection...');
        ws.close();
      }, 5000);
    }
  }
  
  // Start sending test messages
  setTimeout(sendNextMessage, 500);
});

ws.on('message', (data) => {
  console.log('📨 Received response:');
  
  try {
    const message = JSON.parse(data.toString());
    console.log('   📋 JSON:', JSON.stringify(message, null, 2));
    
    // Look for helpful information in the response
    if (message.type === 'error' && message.message) {
      console.log(`   💡 Error hint: ${message.message}`);
    }
    if (message.supported_types) {
      console.log(`   💡 Supported types: ${JSON.stringify(message.supported_types)}`);
    }
    if (message.config || message.configuration) {
      console.log(`   💡 Config info: ${JSON.stringify(message.config || message.configuration)}`);
    }
  } catch (error) {
    console.log('   📋 Raw data:', data.toString());
    console.log('   📋 Data length:', data.length);
  }
});

ws.on('error', (error) => {
  console.error('❌ WebSocket error:', error.message);
});

ws.on('close', (code, reason) => {
  console.log(`\n🔌 Connection closed`);
  console.log(`   📋 Code: ${code}`);
  console.log(`   📋 Reason: ${reason}`);
  process.exit(0);
});

// Safety timeout
setTimeout(() => {
  console.log('\n⏰ Safety timeout - closing...');
  ws.close();
  process.exit(0);
}, 15000);

process.on('SIGINT', () => {
  console.log('\n🛑 Interrupted - closing...');
  ws.close();
  process.exit(0);
});

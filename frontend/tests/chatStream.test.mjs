import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const Module = require('module');

function loadChatStreamModule() {
  const filename = resolve('lib/chatStream.ts');
  const previous = Module._extensions['.ts'];
  Module._extensions['.ts'] = (mod, childFilename) => {
    const source = readFileSync(childFilename, 'utf8');
    const output = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    }).outputText;
    mod.filename = childFilename;
    mod.paths = Module._nodeModulePaths(dirname(childFilename));
    mod._compile(output, childFilename);
  };
  delete require.cache[filename];
  const loaded = require(filename);
  Module._extensions['.ts'] = previous;
  return loaded;
}

function chunkedResponse(chunks) {
  const encoder = new TextEncoder();
  return new Response(new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  }), { headers: { 'Content-Type': 'text/event-stream' } });
}

test('chat stream parser handles split events and returns the final payload', async () => {
  const { readChatStream } = loadChatStreamModule();
  const statuses = [];
  const response = chunkedResponse([
    'data: {"type":"status","message":"Loading',
    ' data..."}\n\ndata: {"type":"final",',
    '"payload":{"answer":"Done"}}\n\n',
  ]);

  const payload = await readChatStream(response, (message) => statuses.push(message));

  assert.deepEqual(statuses, ['Loading data...']);
  assert.equal(payload.answer, 'Done');
});

test('chat stream parser surfaces error events', async () => {
  const { readChatStream } = loadChatStreamModule();
  const response = chunkedResponse([
    'data: {"type":"error","message":"Research failed"}\n\n',
  ]);

  await assert.rejects(() => readChatStream(response), /Research failed/);
});

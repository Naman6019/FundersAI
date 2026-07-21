import type { CanvasPayload } from '@/types/funds';

export interface ChatApiResponse extends CanvasPayload {
  answer: string;
  system_action?: {
    type?: string;
    ids?: string[];
  } | null;
  conversation_context?: Record<string, unknown> | null;
  source_freshness?: unknown;
  data_quality?: unknown;
  risk_analysis?: unknown;
  confidence?: unknown;
  trace_id?: unknown;
  coverage_status?: unknown;
  model_status?: unknown;
  status_flag?: unknown;
  resolution?: unknown;
  explanation_mode?: unknown;
  answer_mode?: unknown;
  news_context_status?: unknown;
  sources?: unknown;
  reasoning_summary?: unknown;
  response_message_id?: string;
}

type ChatStreamEvent = {
  type?: string;
  message?: string;
  payload?: ChatApiResponse;
};

function parseEvent(frame: string): ChatStreamEvent | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');
  if (!data) return null;

  try {
    return JSON.parse(data) as ChatStreamEvent;
  } catch {
    throw new Error('The research service returned an invalid stream event.');
  }
}

export async function readChatStream(
  response: Response,
  onStatus?: (message: string) => void,
): Promise<ChatApiResponse> {
  if (!response.body) {
    throw new Error('The research service returned an empty response.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalPayload: ChatApiResponse | null = null;

  const handleFrame = (frame: string) => {
    const event = parseEvent(frame);
    if (!event) return;
    if (event.type === 'status' && event.message) {
      onStatus?.(event.message);
      return;
    }
    if (event.type === 'error') {
      throw new Error(event.message || 'FundersAI research service could not complete the request.');
    }
    if (event.type === 'final' && event.payload) {
      finalPayload = event.payload;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.search(/\r?\n\r?\n/);
    while (boundary >= 0) {
      const frame = buffer.slice(0, boundary);
      const delimiter = buffer.slice(boundary).match(/^(?:\r?\n){2}/)?.[0] || '\n\n';
      buffer = buffer.slice(boundary + delimiter.length);
      handleFrame(frame);
      boundary = buffer.search(/\r?\n\r?\n/);
    }
  }

  buffer += decoder.decode();
  if (buffer.trim()) handleFrame(buffer);
  if (!finalPayload) throw new Error('No final response was received from the research service.');
  return finalPayload;
}

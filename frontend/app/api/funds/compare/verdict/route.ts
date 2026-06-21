import { proxyPost } from '../../../quant/proxy';

export async function POST(request: Request) {
  return proxyPost('/api/funds/compare/verdict', request);
}

import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const baseUrl = process.env.PORTFOLIO_E2E_BASE_URL || 'http://127.0.0.1:3000';

assert.ok(supabaseUrl && anonKey && serviceKey, 'Supabase environment variables are required');
assert.equal(
  process.env.PORTFOLIO_E2E_CONFIRM_PRODUCTION,
  '1',
  'Set PORTFOLIO_E2E_CONFIRM_PRODUCTION=1 to allow temporary production test users and rows',
);

const admin = createClient(supabaseUrl, serviceKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});
const anon = createClient(supabaseUrl, anonKey, {
  auth: { persistSession: false, autoRefreshToken: false },
});

const suffix = `${Date.now()}-${randomUUID().slice(0, 8)}`;
const password = `Portfolio-${randomUUID()}-9a!`;
const users = [];

async function createUser(label) {
  const email = `portfolio-e2e-${suffix}-${label}@example.com`;
  const { data, error } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
  });
  assert.ifError(error);
  assert.ok(data.user);
  users.push(data.user.id);

  const client = createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const signIn = await client.auth.signInWithPassword({ email, password });
  assert.ifError(signIn.error);
  assert.ok(signIn.data.session?.access_token);
  return {
    id: data.user.id,
    token: signIn.data.session.access_token,
    client,
  };
}

async function api(token, path, init = {}) {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { 'content-type': 'application/json' } : {}),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await response.json();
  return { response, body };
}

try {
  const userA = await createUser('a');
  const userB = await createUser('b');

  const anonymousApi = await api(null, '/api/portfolio');
  assert.equal(anonymousApi.response.status, 401);

  const anonymousRows = await anon.from('portfolios').select('id');
  assert.equal(anonymousRows.error?.code, '42501');

  const spoofedOwner = await userA.client.from('portfolios').insert({
    user_id: userB.id,
    name: 'Forbidden owner spoof',
  });
  assert.equal(spoofedOwner.error?.code, '42501');

  const created = await api(userA.token, '/api/portfolio', {
    method: 'POST',
    body: JSON.stringify({ name: 'Phase one production smoke' }),
  });
  assert.equal(created.response.status, 201);
  const portfolioId = created.body.portfolio.id;

  const positionCreated = await api(userA.token, `/api/portfolio/${portfolioId}/positions`, {
    method: 'POST',
    body: JSON.stringify({ scheme_code: 119551, units: 12.5, current_value: 25000 }),
  });
  assert.equal(positionCreated.response.status, 201);
  assert.equal(positionCreated.body.position.position_source, 'manual');
  const positionId = positionCreated.body.position.id;

  const ownerList = await api(userA.token, '/api/portfolio');
  assert.equal(ownerList.response.status, 200);
  assert.ok(ownerList.body.portfolios.some((row) => row.id === portfolioId));

  const secondUserList = await api(userB.token, '/api/portfolio');
  assert.equal(secondUserList.response.status, 200);
  assert.ok(!secondUserList.body.portfolios.some((row) => row.id === portfolioId));

  const forbiddenChildRead = await api(userB.token, `/api/portfolio/${portfolioId}/positions`);
  assert.equal(forbiddenChildRead.response.status, 404);

  const forbiddenChildInsert = await userB.client.from('portfolio_positions').insert({
    portfolio_id: portfolioId,
    scheme_code: 118989,
    units: 1,
    current_value: 1,
    position_source: 'manual',
  });
  assert.equal(forbiddenChildInsert.error?.code, '42501');

  const forbiddenPatch = await api(
    userB.token,
    `/api/portfolio/${portfolioId}/positions/${positionId}`,
    { method: 'PATCH', body: JSON.stringify({ current_value: 1 }) },
  );
  assert.equal(forbiddenPatch.response.status, 404);

  const ownerPatch = await api(
    userA.token,
    `/api/portfolio/${portfolioId}/positions/${positionId}`,
    { method: 'PATCH', body: JSON.stringify({ units: 13, current_value: 26000 }) },
  );
  assert.equal(ownerPatch.response.status, 200);
  assert.equal(Number(ownerPatch.body.position.units), 13);

  const ownerDelete = await api(
    userA.token,
    `/api/portfolio/${portfolioId}/positions/${positionId}`,
    { method: 'DELETE' },
  );
  assert.equal(ownerDelete.response.status, 200);

  console.log('Portfolio phase-one production E2E passed: auth, CRUD, RLS isolation, and manual source.');
} finally {
  for (const userId of users.reverse()) {
    const { error } = await admin.auth.admin.deleteUser(userId);
    if (error) console.error(`Temporary user cleanup failed for ${userId}: ${error.message}`);
  }
}

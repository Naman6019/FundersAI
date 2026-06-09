import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const Module = require('module');

function installTsLoader() {
  const previous = Module._extensions['.ts'];
  Module._extensions['.ts'] = (mod, filename) => {
    const source = readFileSync(filename, 'utf8');
    const output = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    }).outputText;
    mod.filename = filename;
    mod.paths = Module._nodeModulePaths(dirname(filename));
    mod._compile(output, filename);
  };
  return () => {
    Module._extensions['.ts'] = previous;
  };
}

test('billing migration adds ultra tier and billing tables', () => {
  const migration = readFileSync(resolve('../backend/migrations/20260608_add_billing_subscriptions.sql'), 'utf8');
  assert.match(migration, /tier in \('free', 'pro', 'ultra'\)/);
  assert.match(migration, /create table if not exists public\.billing_subscriptions/);
  assert.match(migration, /create table if not exists public\.billing_events/);
  assert.match(migration, /unique \(provider, event_id\)/);
});

test('Razorpay webhook signature helper validates raw body HMAC', () => {
  process.env.RAZORPAY_WEBHOOK_SECRET = 'secret_test';
  const restore = installTsLoader();
  const helpers = require(resolve('lib/billing/razorpay.ts'));
  restore();

  const raw = JSON.stringify({ event: 'subscription.activated' });
  const signature = crypto.createHmac('sha256', 'secret_test').update(raw).digest('hex');
  assert.equal(helpers.verifyRazorpayWebhookSignature(raw, signature), true);
  assert.equal(helpers.verifyRazorpayWebhookSignature(raw, 'bad'), false);
});

test('billing API routes enforce auth, tier validation, and webhook-only activation', () => {
  const subscriptionRoute = readFileSync(resolve('app/api/billing/subscriptions/route.ts'), 'utf8');
  const webhookRoute = readFileSync(resolve('app/api/billing/webhook/route.ts'), 'utf8');
  const razorpayHelpers = readFileSync(resolve('lib/billing/razorpay.ts'), 'utf8');

  assert.match(subscriptionRoute, /getUserContext\(request\)/);
  assert.match(subscriptionRoute, /status: 401/);
  assert.match(subscriptionRoute, /isPaidTier\(tier\)/);
  assert.match(subscriptionRoute, /status: 400/);
  assert.match(subscriptionRoute, /createRazorpaySubscription/);
  assert.match(razorpayHelpers, /\.subscriptions\.create/);
  assert.doesNotMatch(razorpayHelpers, /\/v1\/subscriptions/);
  assert.doesNotMatch(subscriptionRoute, /user_profiles'\)\.update\(\{ tier/);
  assert.doesNotMatch(subscriptionRoute, /amount: tierConfig\.amountPaise/);
  assert.doesNotMatch(subscriptionRoute, /currency: 'INR'/);
  assert.doesNotMatch(subscriptionRoute, /order_id/);

  assert.match(webhookRoute, /verifyRazorpayWebhookSignature/);
  assert.match(webhookRoute, /billing_events/);
  assert.match(webhookRoute, /duplicate: true/);
  assert.match(webhookRoute, /syncUserTierFromBilling/);
  assert.match(webhookRoute, /\.eq\('status', 'active'\)/);
});

test('billing UI renders tiers and opens checkout with returned subscription id', () => {
  const tiers = readFileSync(resolve('lib/billing/tiers.ts'), 'utf8');
  const billingPage = readFileSync(resolve('components/billing/BillingPage.tsx'), 'utf8');

  assert.match(tiers, /₹99\/month/);
  assert.match(tiers, /₹149\/month/);
  assert.match(billingPage, /checkout\.razorpay\.com\/v1\/checkout\.js/);
  assert.match(billingPage, /new window\.Razorpay/);
  assert.match(billingPage, /subscription_id/);
  assert.match(billingPage, /subscription_checkout_received_order_id/);
  assert.match(billingPage, /invalid_subscription_id/);
  assert.match(billingPage, /\[razorpay:checkout:subscription\]/);
  assert.match(billingPage, /\[razorpay:checkout:success\]/);
  assert.match(billingPage, /Payment authorised/);
  assert.doesNotMatch(billingPage, /StandardCheckoutPanel/);
});

test('Razorpay subscription helpers reject invalid plan and subscription identifiers', () => {
  process.env.RAZORPAY_KEY_ID = 'rzp_test_key';
  process.env.RAZORPAY_KEY_SECRET = 'secret_test';
  const restore = installTsLoader();
  const helpers = require(resolve('lib/billing/razorpay.ts'));
  restore();

  assert.doesNotThrow(() => helpers.assertRazorpayPlanId('plan_test'));
  assert.throws(() => helpers.assertRazorpayPlanId('pro'), /invalid_razorpay_plan_id/);
  assert.doesNotThrow(() => helpers.assertRazorpaySubscription({ id: 'sub_test', status: 'created' }));
  assert.throws(() => helpers.assertRazorpaySubscription({ id: 'order_test', status: 'created' }), /invalid_razorpay_subscription_id/);
  assert.throws(() => helpers.assertRazorpaySubscription({ id: 'sub_test' }), /invalid_razorpay_subscription_status:missing/);
});

test('standard checkout creates orders and verifies payment signatures server-side', () => {
  process.env.RAZORPAY_KEY_SECRET = 'secret_test';
  const restore = installTsLoader();
  const helpers = require(resolve('lib/billing/razorpay.ts'));
  restore();

  const orderId = 'order_test';
  const paymentId = 'pay_test';
  const signature = crypto.createHmac('sha256', 'secret_test').update(`${orderId}|${paymentId}`).digest('hex');
  assert.equal(helpers.verifyRazorpayPaymentSignature({ orderId, paymentId, signature }), true);
  assert.equal(helpers.verifyRazorpayPaymentSignature({ orderId, paymentId, signature: 'bad' }), false);

  const createOrderRoute = readFileSync(resolve('app/api/create-order/route.ts'), 'utf8');
  const verifyPaymentRoute = readFileSync(resolve('app/api/verify-payment/route.ts'), 'utf8');
  const checkoutPanel = readFileSync(resolve('components/billing/StandardCheckoutPanel.tsx'), 'utf8');

  assert.match(createOrderRoute, /amount < 100/);
  assert.match(createOrderRoute, /createRazorpayOrder/);
  assert.match(createOrderRoute, /order_id: order\.id/);
  assert.match(verifyPaymentRoute, /verifyRazorpayPaymentSignature/);
  assert.match(verifyPaymentRoute, /signature_mismatch/);
  assert.match(checkoutPanel, /checkout\.razorpay\.com\/v1\/checkout\.js/);
  assert.match(checkoutPanel, /\/api\/create-order/);
  assert.match(checkoutPanel, /\/api\/verify-payment/);
  assert.match(checkoutPanel, /payment\.failed/);
});

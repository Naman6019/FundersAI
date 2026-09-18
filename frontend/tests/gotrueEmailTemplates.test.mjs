import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const templates = [
  { file: 'confirmation.html', title: 'Confirm your email', variable: '.Email' },
  { file: 'recovery.html', title: 'Reset your password', variable: '.Email' },
  { file: 'magic-link.html', title: 'Your secure sign-in link', variable: '.Email' },
  { file: 'invite.html', title: 'You are invited to FundersAI', variable: '.Email' },
  { file: 'email-change.html', title: 'Confirm your new email', variable: '.NewEmail' },
];

const forbiddenTemplateValues = /{{\s*\.(?:Token|TokenHash|SiteURL|RedirectTo)\s*}}/;

for (const { file, title, variable } of templates) {
  test(`${file} keeps GoTrue's complete confirmation URL intact`, () => {
    const html = readFileSync(
      new URL(`../public/email-templates/${file}`, import.meta.url),
      'utf8',
    );

    assert.match(html, new RegExp(`<title>${title}</title>`));
    assert.match(html, new RegExp(`{{ ${variable} }}`));
    assert.equal((html.match(/href="{{ \.ConfirmationURL }}"/g) ?? []).length, 2);
    assert.equal((html.match(/{{ \.ConfirmationURL }}/g) ?? []).length, 3);
    assert.doesNotMatch(html, forbiddenTemplateValues);
    assert.doesNotMatch(html, /auth\/v1\/verify|redirect_to=/i);
  });
}

test('password recovery still redirects through the app callback', () => {
  const authForm = readFileSync(
    new URL('../components/auth/AuthForm.tsx', import.meta.url),
    'utf8',
  );

  assert.match(
    authForm,
    /redirectTo: `\$\{window\.location\.origin\}\/auth\/callback\?next=\/auth\/reset-password`/,
  );
});

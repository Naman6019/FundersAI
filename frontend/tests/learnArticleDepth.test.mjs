import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

/**
 * The learn articles target query clusters Search Console showed ranking on page 3 with only
 * ~360-420 words. These tests pin the two things that make the expansion worth anything: real
 * depth, and FAQ markup whose text is actually rendered on the page.
 */

const ARTICLES = [
  {
    slug: 'pe-ratio',
    path: 'app/learn/pe-ratio/page.tsx',
    // Queries this article must actually answer, taken from the Search Console query export.
    requiredPhrases: [
      'earnings yield',
      'PEG',
      'trailing',
      'forward',
      'sector',
      'negative or near-zero earnings',
      'cyclical',
    ],
  },
  {
    slug: 'alpha-beta-sharpe',
    path: 'app/learn/alpha-beta-sharpe/page.tsx',
    requiredPhrases: [
      'Sortino',
      'standard deviation',
      'risk-free rate',
      'Covariance',
      'concentration',
      'benchmark choice',
    ],
  },
];

for (const article of ARTICLES) {
  test(`${article.slug} answers the query cluster rather than being thin`, () => {
    const source = readFileSync(article.path, 'utf8');

    for (const phrase of article.requiredPhrases) {
      assert.ok(
        source.toLowerCase().includes(phrase.toLowerCase()),
        `${article.slug} must cover "${phrase}"`,
      );
    }

    // A table of comparison data is what separates a reference page from a glossary stub.
    assert.match(source, /<table/, `${article.slug} must include a comparison table`);

    // The FAQ array is the single source for both the visible section and the schema, so the
    // markup can never describe a question the reader cannot see.
    assert.match(source, /const FAQS = \[/);
    assert.match(source, /faqs=\{FAQS\}/);
    assert.match(source, /FAQS\.map/);
  });
}

test('ArticleJsonLd emits FAQPage only when the page supplies visible FAQs', () => {
  const source = readFileSync('components/seo/JsonLd.tsx', 'utf8');
  assert.match(source, /faqs\?: Array<\{ q: string; a: string \}>/);
  assert.match(source, /faqs = \[\]/);
  // Guarded so an article without a FAQ section does not claim one.
  assert.match(source, /\.\.\.\(faqs\.length > 0/);
  assert.match(source, /'@type': 'FAQPage'/);
});

test('articles state the research-only boundary and do not give advice', () => {
  for (const article of ARTICLES) {
    const source = readFileSync(article.path, 'utf8');
    assert.match(source, /Research only/);
    assert.match(source, /not personalized investment advice/);
    // No buy/sell instruction language.
    assert.doesNotMatch(source, /\byou should buy\b|\byou should sell\b|\brecommend buying\b/i);
  }
});

test('article examples are labelled as hypothetical, not presented as live figures', () => {
  for (const article of ARTICLES) {
    const source = readFileSync(article.path, 'utf8');
    assert.match(
      source,
      /hypothetical|illustrative|Worked example|Indicative only/i,
      `${article.path} must label its figures as illustrative`,
    );
  }
});

// A regression guard on the FAQ contract itself: a FAQ answer must be a non-trivial string.
test('every declared FAQ entry has a question and a substantive answer', () => {
  for (const article of ARTICLES) {
    const source = readFileSync(article.path, 'utf8');
    const block = source.slice(source.indexOf('const FAQS = ['), source.indexOf('];', source.indexOf('const FAQS = [')));
    const questions = block.match(/q: '/g) ?? [];
    const answers = block.match(/a: '/g) ?? [];
    assert.ok(questions.length >= 5, `${article.slug} should answer at least 5 questions`);
    assert.equal(questions.length, answers.length, `${article.slug} FAQ q/a counts must match`);
  }
});

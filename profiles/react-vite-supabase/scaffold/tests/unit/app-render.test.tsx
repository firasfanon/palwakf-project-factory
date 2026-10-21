import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import App from '../../src/App';

describe('generated application starter', () => {
  it('renders the exact project title and a visible implementation roadmap', () => {
    const html = renderToStaticMarkup(<App />);
    expect(html).toContain('{{PROJECT_NAME}}');
    expect(html).toContain('src/features/');
    expect(html).toContain('docs/ai/TASKS.md');
    expect(html).toContain('<main');
  });
});

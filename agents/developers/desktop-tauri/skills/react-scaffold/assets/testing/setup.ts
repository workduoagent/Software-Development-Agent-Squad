/**
 * vitest 全局初始化（复制到项目 src/test/setup.ts）
 * - jest-dom 断言扩展（toBeInTheDocument 等）
 * - 每个用例后卸载组件树，避免跨用例 DOM 污染
 */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
});

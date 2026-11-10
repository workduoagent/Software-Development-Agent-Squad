/**
 * useTheme：主题唯一操作入口。
 * 切换只允许调 setTheme()，禁止组件直接改 documentElement.className；
 * 业务组件只消费 resolvedTheme / mode，自定义样式靠 .light / .dark 下的 CSS 变量自动适配，不必写两套。
 */
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store';
import { setTheme, type ResolvedTheme, type ThemeMode } from '@/store/slices/themeSlice';

export type { ResolvedTheme, ThemeMode };

export interface UseThemeResult {
  /** 用户选择的模式：light / dark / system */
  mode: ThemeMode;
  /** 实际生效的主题：light / dark */
  resolvedTheme: ResolvedTheme;
  /** 切换主题 */
  setTheme: (mode: ThemeMode) => void;
  /** 明暗互切（在 light / dark 之间切换，system 会先落到当前解析结果） */
  toggleTheme: () => void;
}

export function useTheme(): UseThemeResult {
  const dispatch = useAppDispatch();
  const mode = useAppSelector((state) => state.theme.mode);
  const systemTheme = useAppSelector((state) => state.system.resolved);

  const resolvedTheme: ResolvedTheme = mode === 'system' ? systemTheme : mode;

  const handleSetTheme = useCallback(
    (next: ThemeMode) => {
      dispatch(setTheme(next));
    },
    [dispatch],
  );

  const toggleTheme = useCallback(() => {
    dispatch(setTheme(resolvedTheme === 'dark' ? 'light' : 'dark'));
  }, [dispatch, resolvedTheme]);

  return { mode, resolvedTheme, setTheme: handleSetTheme, toggleTheme };
}

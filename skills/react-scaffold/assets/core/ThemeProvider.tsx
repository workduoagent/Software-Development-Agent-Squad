/**
 * ThemeProvider：主题运行时的唯一执行者，也是唯一允许做以下三件事的地方：
 * 监听系统主题变化写入 systemSlice、把 resolvedTheme 反映到 <html> 的 .light / .dark、驱动 antd 算法与 token。
 * 业务组件与 hooks 严禁直接改 documentElement.className。
 */
import { useEffect, useMemo } from 'react';
import { ConfigProvider, App as AntdApp, theme as antdTheme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useAppDispatch, useAppSelector } from '@/store';
import { setSystemTheme } from '@/store/slices/systemSlice';
import type { ResolvedTheme } from '@/store/slices/themeSlice';

interface ThemeProviderProps {
  children: React.ReactNode;
}

/** antd 主题 token：与 styles/theme.css 中的 CSS 变量保持同色系 */
const antdTokens = {
  light: {
    colorPrimary: '#4f46e5',
    colorSuccess: '#52c41a',
    colorWarning: '#faad14',
    colorError: '#ff4d4f',
    // info 跟随主色：另留一支蓝，只会让人分不清「这是提示」还是「这能点」
    colorInfo: '#4f46e5',
    borderRadius: 8,
    fontSize: 14,
  },
  dark: {
    colorPrimary: '#6366f1',
    colorSuccess: '#73d13d',
    colorWarning: '#ffc069',
    colorError: '#ff7875',
    colorInfo: '#6366f1',
    borderRadius: 8,
    fontSize: 14,
  },
} as const;

export function ThemeProvider({ children }: ThemeProviderProps) {
  const dispatch = useAppDispatch();
  const mode = useAppSelector((state) => state.theme.mode);
  const systemResolved = useAppSelector((state) => state.system.resolved);

  const resolvedTheme: ResolvedTheme = mode === 'system' ? systemResolved : mode;

  /** 监听系统主题变化，把解析结果写进 systemSlice */
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = (event: MediaQueryListEvent) => {
      dispatch(setSystemTheme(event.matches ? 'dark' : 'light'));
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [dispatch]);

  /** 把解析结果写到 <html> 的 class 上，供 CSS 变量切换 */
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolvedTheme);
    // 同步浏览器原生滚动条 / 表单控件配色
    root.style.colorScheme = resolvedTheme;
  }, [resolvedTheme]);

  /** antd 算法与 token 跟随解析结果切换 */
  const themeConfig = useMemo(() => {
    const isDark = resolvedTheme === 'dark';
    return {
      algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
      token: antdTokens[resolvedTheme],
    };
  }, [resolvedTheme]);

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      {/* AntdApp 提供 message / notification / modal 的静态方法上下文 */}
      <AntdApp>{children}</AntdApp>
    </ConfigProvider>
  );
}

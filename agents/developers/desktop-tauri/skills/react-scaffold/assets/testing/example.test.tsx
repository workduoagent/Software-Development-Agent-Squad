/**
 * 四态闭环示范测试（复制到项目 tests/example.test.tsx，参考写法后替换为业务测试）。
 * 演示 Loading / Empty / Error(可重试) / Success 四态与 axios-mock-adapter 拦截。
 * 真实项目：组件从 src 导入，Mock 复用项目 mock 体系（src/api/mock）或独立 MockAdapter 实例。
 */
import { useEffect, useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';

interface User {
  id: string;
  nickname: string;
}

const http = axios.create({ baseURL: '/api' });
let mock: MockAdapter;

/** 示范组件：列表加载四态 */
function UserList() {
  const [state, setState] = useState<'loading' | 'empty' | 'error' | 'success'>('loading');
  const [users, setUsers] = useState<User[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    http
      .get<{ code: number; msg: string; data: User[] }>('/v1/users')
      .then((res) => {
        if (cancelled) return;
        const list = res.data.data ?? [];
        setUsers(list);
        setState(list.length > 0 ? 'success' : 'empty');
      })
      .catch(() => {
        if (!cancelled) setState('error');
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  if (state === 'loading') return <p>加载中…</p>;
  if (state === 'error') {
    return (
      <button type="button" onClick={() => setTick((t) => t + 1)}>
        加载失败，点击重试
      </button>
    );
  }
  if (state === 'empty') return <p>暂无数据</p>;
  return (
    <ul>
      {users.map((u) => (
        <li key={u.id}>{u.nickname}</li>
      ))}
    </ul>
  );
}

describe('UserList 四态闭环', () => {
  beforeEach(() => {
    mock = new MockAdapter(http);
  });

  afterEach(() => {
    mock.restore();
  });

  it('Success 态：渲染用户列表', async () => {
    mock.onGet('/v1/users').reply(200, {
      code: 0,
      msg: 'ok',
      data: [
        { id: '7311234567890123456', nickname: '张三' },
        { id: '7311234567890123457', nickname: '李四' },
      ],
    });
    render(<UserList />);
    expect(await screen.findByText('张三')).toBeInTheDocument();
    expect(screen.getByText('李四')).toBeInTheDocument();
  });

  it('Empty 态：空数组显示空态提示', async () => {
    mock.onGet('/v1/users').reply(200, { code: 0, msg: 'ok', data: [] });
    render(<UserList />);
    expect(await screen.findByText('暂无数据')).toBeInTheDocument();
  });

  it('Error 态：接口 500 显示重试按钮，点击后恢复成功', async () => {
    mock.onGet('/v1/users').replyOnce(500);
    render(<UserList />);
    const retry = await screen.findByRole('button', { name: /点击重试/ });

    mock.onGet('/v1/users').reply(200, {
      code: 0,
      msg: 'ok',
      data: [{ id: '7311234567890123458', nickname: '王五' }],
    });
    await userEvent.click(retry);
    expect(await screen.findByText('王五')).toBeInTheDocument();
  });
});

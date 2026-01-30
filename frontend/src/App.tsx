/**
 * Main App Component with Routing
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, Layout, Menu } from 'antd';
import { AppstoreOutlined, FileTextOutlined, HistoryOutlined } from '@ant-design/icons';
import { useState } from 'react';
import TaskList from './pages/TaskList';
import TaskCreate from './pages/TaskCreate';
import TaskDetail from './pages/TaskDetail';
import './App.css';

const { Header, Content, Sider } = Layout;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#1890ff',
          },
        }}
      >
        <BrowserRouter>
          <Layout style={{ minHeight: '100vh' }}>
            <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
              <div style={{ color: 'white', fontSize: '20px', fontWeight: 'bold' }}>
                🕷️ Crawl4AI - WeChat Console
              </div>
            </Header>
            <Layout>
              <Sider
                collapsible
                collapsed={collapsed}
                onCollapse={setCollapsed}
                style={{ background: '#fff' }}
              >
                <Menu
                  mode="inline"
                  defaultSelectedKeys={['tasks']}
                  style={{ height: '100%', borderRight: 0 }}
                  items={[
                    {
                      key: 'tasks',
                      icon: <AppstoreOutlined />,
                      label: '任务管理',
                      onClick: () => window.location.href = '/',
                    },
                    {
                      key: 'articles',
                      icon: <FileTextOutlined />,
                      label: '文章列表',
                      disabled: true,
                    },
                    {
                      key: 'history',
                      icon: <HistoryOutlined />,
                      label: '执行历史',
                      disabled: true,
                    },
                  ]}
                />
              </Sider>
              <Layout style={{ padding: '24px' }}>
                <Content
                  style={{
                    background: '#fff',
                    padding: 24,
                    margin: 0,
                    minHeight: 280,
                    borderRadius: 8,
                  }}
                >
                  <Routes>
                    <Route path="/" element={<TaskList />} />
                    <Route path="/tasks/create" element={<TaskCreate />} />
                    <Route path="/tasks/:id" element={<TaskDetail />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Content>
              </Layout>
            </Layout>
          </Layout>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;

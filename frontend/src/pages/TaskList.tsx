/**
 * Task List Page - Main Dashboard
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Table,
  Button,
  Space,
  Tag,
  Popconfirm,
  message,
  Select,
  Input,
  Card,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  EyeOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { taskAPI } from '../api/client';
import type { Task } from '../types';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/zh-cn';

dayjs.extend(relativeTime);
dayjs.locale('zh-cn');

const { Search } = Input;

export default function TaskList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Fetch tasks
  const { data, isLoading } = useQuery({
    queryKey: ['tasks', page, statusFilter],
    queryFn: () =>
      taskAPI.listTasks({
        skip: (page - 1) * pageSize,
        limit: pageSize,
        status: statusFilter,
      }),
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: taskAPI.deleteTask,
    onSuccess: () => {
      message.success('任务已删除');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: () => {
      message.error('删除失败');
    },
  });

  // Update status mutation
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      taskAPI.updateStatus(id, status),
    onSuccess: () => {
      message.success('状态已更新');
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: () => {
      message.error('更新失败');
    },
  });

  // Execute mutation
  const executeMutation = useMutation({
    mutationFn: taskAPI.executeTask,
    onSuccess: () => {
      message.success('任务已开始执行');
    },
    onError: () => {
      message.error('执行失败');
    },
  });

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string, record: Task) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.description && (
            <div style={{ fontSize: '12px', color: '#888' }}>{record.description}</div>
          )}
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          active: { color: 'green', text: '运行中' },
          paused: { color: 'orange', text: '已暂停' },
          deleted: { color: 'red', text: '已删除' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '计划类型',
      dataIndex: 'schedule_type',
      key: 'schedule_type',
      width: 120,
      render: (type: string, record: Task) => {
        const typeMap: Record<string, string> = {
          once: '单次',
          interval: '间隔',
          cron: 'Cron',
        };
        return (
          <div>
            <div>{typeMap[type] || type}</div>
            {type === 'interval' && record.schedule_config.hours && (
              <div style={{ fontSize: '12px', color: '#888' }}>
                每 {record.schedule_config.hours} 小时
              </div>
            )}
            {type === 'cron' && record.schedule_config.cron && (
              <div style={{ fontSize: '12px', color: '#888', fontFamily: 'monospace' }}>
                {record.schedule_config.cron}
              </div>
            )}
          </div>
        );
      },
    },
    {
      title: '上次运行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      width: 120,
      render: (time: string) =>
        time ? (
          <div>
            <div>{dayjs(time).format('MM-DD HH:mm')}</div>
            <div style={{ fontSize: '12px', color: '#888' }}>{dayjs(time).fromNow()}</div>
          </div>
        ) : (
          <span style={{ color: '#ccc' }}>未运行</span>
        ),
    },
    {
      title: '下次运行',
      dataIndex: 'next_run_at',
      key: 'next_run_at',
      width: 120,
      render: (time: string) =>
        time ? (
          <div>
            <div>{dayjs(time).format('MM-DD HH:mm')}</div>
            <div style={{ fontSize: '12px', color: '#888' }}>{dayjs(time).fromNow()}</div>
          </div>
        ) : (
          <span style={{ color: '#ccc' }}>-</span>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_: any, record: Task) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/tasks/${record.id}`)}
          >
            详情
          </Button>
          <Button
            type="link"
            size="small"
            icon={<ThunderboltOutlined />}
            onClick={() => executeMutation.mutate(record.id)}
          >
            执行
          </Button>
          <Button
            type="link"
            size="small"
            icon={record.status === 'active' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() =>
              statusMutation.mutate({
                id: record.id,
                status: record.status === 'active' ? 'paused' : 'active',
              })
            }
          >
            {record.status === 'active' ? '暂停' : '恢复'}
          </Button>
          <Popconfirm
            title="确定删除此任务吗？"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const filteredTasks = data?.tasks.filter((task) =>
    searchText ? task.name.toLowerCase().includes(searchText.toLowerCase()) : true
  );

  const stats = data?.tasks || [];
  const activeCount = stats.filter((t) => t.status === 'active').length;
  const pausedCount = stats.filter((t) => t.status === 'paused').length;

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总任务数" value={data?.total || 0} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="运行中" value={activeCount} valueStyle={{ color: '#3f8600' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="已暂停" value={pausedCount} valueStyle={{ color: '#cf1322' }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="URL总数"
              value={stats.reduce((sum, t) => sum + (t.wechat_urls?.length || 0), 0)}
            />
          </Card>
        </Col>
      </Row>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Search
            placeholder="搜索任务名称"
            allowClear
            style={{ width: 300 }}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <Select
            placeholder="筛选状态"
            style={{ width: 150 }}
            allowClear
            onChange={(value) => setStatusFilter(value)}
            options={[
              { label: '运行中', value: 'active' },
              { label: '已暂停', value: 'paused' },
            ]}
          />
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/tasks/create')}>
          新建任务
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={filteredTasks}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 个任务`,
        }}
      />
    </div>
  );
}

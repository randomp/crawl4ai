/**
 * Task Detail Page - View task details and execution history
 */

import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Descriptions,
  Button,
  Space,
  Tag,
  Table,
  message,
  Popconfirm,
  Tabs,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import { taskAPI } from '../api/client';
import dayjs from 'dayjs';

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const taskId = parseInt(id || '0');

  // Fetch task
  const { data: task, isLoading } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => taskAPI.getTask(taskId),
    enabled: !!taskId,
  });

  // Fetch executions
  const { data: executionsData } = useQuery({
    queryKey: ['executions', taskId],
    queryFn: () => taskAPI.getExecutions(taskId, { skip: 0, limit: 20 }),
    enabled: !!taskId,
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  // Update status mutation
  const statusMutation = useMutation({
    mutationFn: (status: string) => taskAPI.updateStatus(taskId, status),
    onSuccess: () => {
      message.success('状态已更新');
      queryClient.invalidateQueries({ queryKey: ['task', taskId] });
    },
  });

  // Execute mutation
  const executeMutation = useMutation({
    mutationFn: () => taskAPI.executeTask(taskId),
    onSuccess: () => {
      message.success('任务已开始执行');
      queryClient.invalidateQueries({ queryKey: ['executions', taskId] });
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => taskAPI.deleteTask(taskId),
    onSuccess: () => {
      message.success('任务已删除');
      navigate('/');
    },
  });

  // Export function
  const handleExport = async (format: 'excel' | 'csv' | 'json') => {
    try {
      const blob = await taskAPI.exportArticles(taskId, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `articles_${taskId}.${format === 'excel' ? 'xlsx' : format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      message.success('导出成功');
    } catch {
      message.error('导出失败');
    }
  };

  const executionColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusMap: Record<string, { color: string; text: string }> = {
          running: { color: 'blue', text: '运行中' },
          success: { color: 'green', text: '成功' },
          failed: { color: 'red', text: '失败' },
          partial: { color: 'orange', text: '部分成功' },
        };
        const config = statusMap[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '完成时间',
      dataIndex: 'completed_at',
      key: 'completed_at',
      render: (time: string) => (time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'),
    },
    {
      title: '发现',
      dataIndex: 'articles_found',
      key: 'articles_found',
      width: 80,
    },
    {
      title: '新增',
      dataIndex: 'articles_new',
      key: 'articles_new',
      width: 80,
      render: (count: number) => <Tag color="green">{count}</Tag>,
    },
    {
      title: '更新',
      dataIndex: 'articles_updated',
      key: 'articles_updated',
      width: 80,
      render: (count: number) => (count > 0 ? <Tag color="blue">{count}</Tag> : count),
    },
  ];

  if (isLoading || !task) {
    return <Card loading />;
  }

  const statusMap: Record<string, { color: string; text: string }> = {
    active: { color: 'green', text: '运行中' },
    paused: { color: 'orange', text: '已暂停' },
    deleted: { color: 'red', text: '已删除' },
  };

  const latestExecution = executionsData?.executions[0];
  const successCount = executionsData?.executions.filter((e) => e.status === 'success').length || 0;
  const totalExecutions = executionsData?.total || 0;
  const successRate = totalExecutions > 0 ? (successCount / totalExecutions) * 100 : 0;

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
            返回
          </Button>
          <h2 style={{ margin: 0 }}>{task.name}</h2>
          <Tag color={statusMap[task.status].color}>{statusMap[task.status].text}</Tag>
        </div>
        <Space>
          <Button
            icon={<ThunderboltOutlined />}
            onClick={() => executeMutation.mutate()}
            loading={executeMutation.isPending}
          >
            立即执行
          </Button>
          <Button
            icon={task.status === 'active' ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => statusMutation.mutate(task.status === 'active' ? 'paused' : 'active')}
          >
            {task.status === 'active' ? '暂停' : '恢复'}
          </Button>
          <Popconfirm
            title="确定删除此任务吗？"
            onConfirm={() => deleteMutation.mutate()}
            okText="确定"
            cancelText="取消"
          >
            <Button danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic title="总执行次数" value={totalExecutions} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="成功率"
              value={successRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: successRate > 80 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最近新增"
              value={latestExecution?.articles_new || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="URL数量" value={task.wechat_urls?.length || 0} />
          </Card>
        </Col>
      </Row>

      <Tabs
        defaultActiveKey="overview"
        items={[
          {
            key: 'overview',
            label: '概览',
            children: (
              <Card>
                <Descriptions column={2} bordered>
                  <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
                  <Descriptions.Item label="状态">
                    <Tag color={statusMap[task.status].color}>
                      {statusMap[task.status].text}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="计划类型">
                    {task.schedule_type}
                  </Descriptions.Item>
                  <Descriptions.Item label="计划配置">
                    {JSON.stringify(task.schedule_config)}
                  </Descriptions.Item>
                  <Descriptions.Item label="上次运行">
                    {task.last_run_at ? dayjs(task.last_run_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="下次运行">
                    {task.next_run_at ? dayjs(task.next_run_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="创建时间">
                    {dayjs(task.created_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="更新时间">
                    {dayjs(task.updated_at).format('YYYY-MM-DD HH:mm:ss')}
                  </Descriptions.Item>
                  <Descriptions.Item label="描述" span={2}>
                    {task.description || '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="微信URL" span={2}>
                    {task.wechat_urls?.length || 0} 个URL
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'executions',
            label: '执行历史',
            children: (
              <Table
                columns={executionColumns}
                dataSource={executionsData?.executions}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
          {
            key: 'export',
            label: '数据导出',
            children: (
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>选择导出格式：</div>
                  <Space>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleExport('excel')}
                    >
                      导出为 Excel
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleExport('csv')}
                    >
                      导出为 CSV
                    </Button>
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={() => handleExport('json')}
                    >
                      导出为 JSON
                    </Button>
                  </Space>
                </Space>
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}

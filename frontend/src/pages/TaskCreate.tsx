/**
 * Task Create Page - Wizard for creating new tasks
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Steps,
  Form,
  Input,
  Button,
  Upload,
  Select,
  InputNumber,
  message,
  Card,
  Space,
  Tag,
  Alert,
} from 'antd';
import {
  UploadOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd';
import { taskAPI } from '../api/client';
import type { TaskCreateRequest, FileUploadResponse } from '../types';

const { TextArea } = Input;

export default function TaskCreate() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [form] = Form.useForm();
  const [uploadedUrls, setUploadedUrls] = useState<string[]>([]);
  const [uploadResult, setUploadResult] = useState<FileUploadResponse | null>(null);

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => taskAPI.uploadFile(file),
    onSuccess: (data) => {
      setUploadResult(data);
      setUploadedUrls(data.urls);
      message.success(`解析成功！找到 ${data.unique_urls} 个有效URL`);
    },
    onError: () => {
      message.error('文件上传失败');
    },
  });

  // Create task mutation
  const createMutation = useMutation({
    mutationFn: (task: TaskCreateRequest) => taskAPI.createTask(task),
    onSuccess: (data) => {
      message.success('任务创建成功');
      navigate(`/tasks/${data.id}`);
    },
    onError: () => {
      message.error('任务创建失败');
    },
  });

  const handleUpload = (file: UploadFile) => {
    if (file.originFileObj) {
      uploadMutation.mutate(file.originFileObj);
    }
    return false; // Prevent default upload
  };

  const handleNext = async () => {
    try {
      await form.validateFields();
      setCurrentStep(currentStep + 1);
    } catch {
      message.error('请填写所有必填项');
    }
  };

  const handlePrev = () => {
    setCurrentStep(currentStep - 1);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      // Build schedule config
      let schedule_config: Record<string, any> = {};
      if (values.schedule_type === 'interval') {
        schedule_config = { hours: values.interval_hours };
      } else if (values.schedule_type === 'cron') {
        schedule_config = { cron: values.cron_expression };
      } else if (values.schedule_type === 'once') {
        schedule_config = { run_date: values.run_date };
      }

      const taskData: TaskCreateRequest = {
        name: values.name,
        description: values.description,
        schedule_type: values.schedule_type,
        schedule_config,
        wechat_urls: uploadedUrls,
        crawl_config: values.crawl_config ? JSON.parse(values.crawl_config) : {},
      };

      createMutation.mutate(taskData);
    } catch {
      message.error('请检查输入项');
    }
  };

  const steps = [
    {
      title: '基本信息',
      content: (
        <div style={{ maxWidth: 600 }}>
          <Form.Item
            label="任务名称"
            name="name"
            rules={[{ required: true, message: '请输入任务名称' }]}
          >
            <Input placeholder="例如：科技媒体每日采集" />
          </Form.Item>

          <Form.Item label="任务描述" name="description">
            <TextArea
              rows={4}
              placeholder="描述任务的目的和范围"
            />
          </Form.Item>

          <Form.Item label="爬虫配置 (可选)" name="crawl_config">
            <TextArea
              rows={4}
              placeholder='{"cache_mode": "bypass", "word_count_threshold": 100}'
            />
          </Form.Item>
        </div>
      ),
    },
    {
      title: '上传文件',
      content: (
        <div style={{ maxWidth: 600 }}>
          <Alert
            message="上传包含微信公众号URL的Excel或CSV文件"
            description="文件应包含一列微信公众号链接 (https://mp.weixin.qq.com/...)"
            type="info"
            style={{ marginBottom: 16 }}
          />

          <Upload
            beforeUpload={handleUpload}
            maxCount={1}
            accept=".xlsx,.xls,.csv"
          >
            <Button icon={<UploadOutlined />} loading={uploadMutation.isPending}>
              选择文件
            </Button>
          </Upload>

          {uploadResult && (
            <Card style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <strong>文件名：</strong> {uploadResult.filename}
                </div>
                <div>
                  <strong>找到URL：</strong> {uploadResult.urls_found}
                </div>
                <div>
                  <strong>有效URL：</strong> {uploadResult.unique_urls}
                </div>
                <div>
                  <strong>URL预览：</strong>
                  <div style={{ marginTop: 8 }}>
                    {uploadResult.urls.slice(0, 3).map((url, i) => (
                      <Tag key={i} style={{ marginBottom: 4 }}>
                        {url.substring(0, 50)}...
                      </Tag>
                    ))}
                    {uploadResult.urls.length > 3 && (
                      <Tag>+ {uploadResult.urls.length - 3} 更多...</Tag>
                    )}
                  </div>
                </div>
              </Space>
            </Card>
          )}
        </div>
      ),
    },
    {
      title: '配置计划',
      content: (
        <div style={{ maxWidth: 600 }}>
          <Form.Item
            label="计划类型"
            name="schedule_type"
            rules={[{ required: true, message: '请选择计划类型' }]}
            initialValue="interval"
          >
            <Select
              options={[
                { label: '间隔执行', value: 'interval' },
                { label: 'Cron表达式', value: 'cron' },
                { label: '单次执行', value: 'once' },
              ]}
            />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prev, curr) => prev.schedule_type !== curr.schedule_type}
          >
            {() => {
              const scheduleType = form.getFieldValue('schedule_type');

              if (scheduleType === 'interval') {
                return (
                  <Form.Item
                    label="间隔时间（小时）"
                    name="interval_hours"
                    rules={[{ required: true, message: '请输入间隔时间' }]}
                    initialValue={6}
                  >
                    <InputNumber min={1} max={168} style={{ width: '100%' }} />
                  </Form.Item>
                );
              }

              if (scheduleType === 'cron') {
                return (
                  <Form.Item
                    label="Cron表达式"
                    name="cron_expression"
                    rules={[{ required: true, message: '请输入Cron表达式' }]}
                    initialValue="0 */6 * * *"
                  >
                    <Input placeholder="0 */6 * * * (每6小时)" />
                  </Form.Item>
                );
              }

              if (scheduleType === 'once') {
                return (
                  <Form.Item
                    label="执行时间"
                    name="run_date"
                    rules={[{ required: true, message: '请选择执行时间' }]}
                  >
                    <Input type="datetime-local" />
                  </Form.Item>
                );
              }

              return null;
            }}
          </Form.Item>

          <Alert
            message="常用Cron表达式"
            description={
              <ul style={{ marginBottom: 0 }}>
                <li>每小时: 0 * * * *</li>
                <li>每6小时: 0 */6 * * *</li>
                <li>每天凌晨2点: 0 2 * * *</li>
                <li>工作日上午9点: 0 9 * * 1-5</li>
              </ul>
            }
            type="info"
          />
        </div>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/')}>
          返回
        </Button>
        <h2 style={{ margin: 0 }}>创建新任务</h2>
      </div>

      <Card>
        <Steps current={currentStep} items={steps.map((s) => ({ title: s.title }))} />

        <Form form={form} layout="vertical" style={{ marginTop: 32 }}>
          {steps[currentStep].content}
        </Form>

        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'space-between' }}>
          <div>
            {currentStep > 0 && (
              <Button icon={<ArrowLeftOutlined />} onClick={handlePrev}>
                上一步
              </Button>
            )}
          </div>
          <div>
            {currentStep < steps.length - 1 && (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                onClick={handleNext}
                disabled={currentStep === 1 && uploadedUrls.length === 0}
              >
                下一步
              </Button>
            )}
            {currentStep === steps.length - 1 && (
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={handleSubmit}
                loading={createMutation.isPending}
              >
                创建任务
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}

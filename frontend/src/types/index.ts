/**
 * Type definitions for WeChat Article Crawler
 */

export interface Task {
  id: number;
  name: string;
  description?: string;
  status: 'active' | 'paused' | 'deleted';
  schedule_type: 'once' | 'interval' | 'cron';
  schedule_config: Record<string, any>;
  wechat_urls: string[];
  crawl_config?: Record<string, any>;
  source_file?: string;
  last_run_at?: string;
  next_run_at?: string;
  created_at: string;
  updated_at: string;
}

export interface Article {
  id: number;
  task_id: number;
  url: string;
  title: string;
  author: string;
  publish_time?: string;
  content: string;
  content_hash: string;
  metadata?: Record<string, any>;
  crawled_at: string;
  created_at: string;
}

export interface TaskExecution {
  id: number;
  task_id: number;
  status: 'running' | 'success' | 'failed' | 'partial';
  started_at: string;
  completed_at?: string;
  articles_found: number;
  articles_new: number;
  articles_updated: number;
  errors?: any[];
  execution_log?: string;
}

export interface TaskCreateRequest {
  name: string;
  description?: string;
  schedule_type: 'once' | 'interval' | 'cron';
  schedule_config: Record<string, any>;
  wechat_urls: string[];
  crawl_config?: Record<string, any>;
}

export interface TaskUpdateRequest {
  name?: string;
  description?: string;
  schedule_type?: 'once' | 'interval' | 'cron';
  schedule_config?: Record<string, any>;
  wechat_urls?: string[];
  crawl_config?: Record<string, any>;
}

export interface FileUploadResponse {
  filename: string;
  urls_found: number;
  unique_urls: number;
  urls: string[];
}

export interface PaginatedResponse<T> {
  total: number;
  items: T[];
}

export interface TaskListResponse {
  total: number;
  tasks: Task[];
}

export interface ExecutionListResponse {
  total: number;
  executions: TaskExecution[];
}

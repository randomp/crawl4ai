/**
 * API Client for WeChat Article Crawler
 */

import axios from 'axios';
import type {
  Task,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskListResponse,
  ExecutionListResponse,
  FileUploadResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:11235';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Task Management
export const taskAPI = {
  // Upload file
  uploadFile: async (file: File): Promise<FileUploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const { data } = await client.post('/api/tasks/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  // Create task
  createTask: async (task: TaskCreateRequest): Promise<Task> => {
    const { data } = await client.post('/api/tasks', task);
    return data;
  },

  // List tasks
  listTasks: async (params?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<TaskListResponse> => {
    const { data } = await client.get('/api/tasks', { params });
    return data;
  },

  // Get task
  getTask: async (id: number): Promise<Task> => {
    const { data } = await client.get(`/api/tasks/${id}`);
    return data;
  },

  // Update task
  updateTask: async (id: number, updates: TaskUpdateRequest): Promise<Task> => {
    const { data } = await client.put(`/api/tasks/${id}`, updates);
    return data;
  },

  // Delete task
  deleteTask: async (id: number): Promise<void> => {
    await client.delete(`/api/tasks/${id}`);
  },

  // Update status
  updateStatus: async (id: number, status: string): Promise<Task> => {
    const { data } = await client.patch(`/api/tasks/${id}/status`, { status });
    return data;
  },

  // Execute task
  executeTask: async (id: number): Promise<{ message: string; task_id: number }> => {
    const { data } = await client.post(`/api/tasks/${id}/execute`);
    return data;
  },

  // Get executions
  getExecutions: async (
    id: number,
    params?: { skip?: number; limit?: number }
  ): Promise<ExecutionListResponse> => {
    const { data } = await client.get(`/api/tasks/${id}/executions`, { params });
    return data;
  },

  // Export articles
  exportArticles: async (
    id: number,
    format: 'excel' | 'csv' | 'json',
    filters?: { start_date?: string; end_date?: string }
  ): Promise<Blob> => {
    const { data } = await client.get(`/api/tasks/${id}/export`, {
      params: { format, ...filters },
      responseType: 'blob',
    });
    return data;
  },
};

export default client;

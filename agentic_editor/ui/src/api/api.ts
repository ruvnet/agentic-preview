import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update this with your API URL

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getProjects = () => api.get('/projects');
export const createProject = (data: any) => api.post('/projects', data);
export const updateProject = (id: string, data: any) => api.put(`/projects/${id}`, data);
export const deleteProject = (id: string) => api.delete(`/projects/${id}`);
export const getProjectDetails = (id: string) => api.get(`/projects/${id}`);

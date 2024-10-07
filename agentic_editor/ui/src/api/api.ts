import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update this with your API URL

export const api = axios.create({
  baseURL: API_BASE_URL,
});

export const getProjects = () => api.get('/projects');
export const createProject = (data: any) => api.post('/projects', data);
export const updateProject = (id: string, data: any) => api.put(`/projects/${id}`, data);
export const deleteProject = (id: string) => api.delete(`/projects/${id}`);
import axios from 'axios';

const API_BASE_URL = '/api';

export interface Project {
  id: string;
  name: string;
  description: string;
}

export const getProjects = async (): Promise<Project[]> => {
  const response = await axios.get(`${API_BASE_URL}/projects`);
  return response.data;
};

export const getProjectDetails = async (id: string): Promise<Project> => {
  const response = await axios.get(`${API_BASE_URL}/projects/${id}`);
  return response.data;
};

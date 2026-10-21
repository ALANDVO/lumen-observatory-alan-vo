import axios, { AxiosInstance, AxiosError } from 'axios';
import type { Actor, ActorListResponse, ActorSnapshot, ActorTransitionLog, ActorCreate, ActorTransitionRequest, ActorPauseRequest, ActorCommitRequest, ActorResumeRequest, ActorRevertRequest, ActorDumpRequest } from '../types/actor';

const API_BASE = (import.meta as unknown as { env: { VITE_API_BASE: string } }).env?.VITE_API_BASE || '/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const detail = (error.response?.data as Record<string, unknown> | undefined)?.detail;
        const message = typeof detail === 'string' ? detail : error.message;
        return Promise.reject(new Error(message));
      }
    );
  }

  async healthCheck() {
    const response = await this.client.get('/health/');
    return response.data;
  }

  async readinessCheck() {
    const response = await this.client.get('/health/ready');
    return response.data;
  }

  async listActors(params?: {
    skip?: number;
    limit?: number;
    state?: string;
    template_namespace?: string;
    template_name?: string;
    node_name?: string;
  }): Promise<ActorListResponse> {
    const response = await this.client.get('/actors', { params });
    return response.data;
  }

  async getActor(actorUid: string): Promise<Actor> {
    const response = await this.client.get(`/actors/${actorUid}`);
    return response.data;
  }

  async createActor(data: ActorCreate): Promise<Actor> {
    const response = await this.client.post('/actors', data);
    return response.data;
  }

  async transitionActor(actorUid: string, data: ActorTransitionRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/transition`, data);
    return response.data;
  }

  async pauseActor(actorUid: string, data: ActorPauseRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/pause`, data);
    return response.data;
  }

  async commitActor(actorUid: string, data: ActorCommitRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/commit`, data);
    return response.data;
  }

  async resumeActor(actorUid: string, data: ActorResumeRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/resume`, data);
    return response.data;
  }

  async revertActor(actorUid: string, data: ActorRevertRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/revert`, data);
    return response.data;
  }

  async dumpActor(actorUid: string, data: ActorDumpRequest): Promise<Actor> {
    const response = await this.client.post(`/actors/${actorUid}/dump`, data);
    return response.data;
  }

  async deleteActor(actorUid: string): Promise<void> {
    await this.client.delete(`/actors/${actorUid}`);
  }

  async getSnapshots(actorUid: string): Promise<ActorSnapshot[]> {
    const response = await this.client.get(`/actors/${actorUid}/snapshots`);
    return response.data;
  }

  async getTransitions(actorUid: string): Promise<ActorTransitionLog[]> {
    const response = await this.client.get(`/actors/${actorUid}/transitions`);
    return response.data;
  }
}

export const api = new ApiClient();
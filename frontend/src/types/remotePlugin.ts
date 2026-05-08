export interface RemotePlugin {
  id: number;
  name: string;
  display_name: string;
  description: string;
  author: string;
  source_url: string;
  version: string;
  enabled: boolean;
  cleanup_mode: string;
  installed_at: string | null;
}

export interface InstallRequest {
  source_url: string;
}

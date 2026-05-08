export interface RemotePlugin {
  id: number;
  name: string;
  display_name: string;
  description: string;
  author: string;
  source_url: string;
  version: string;
  enabled: boolean;
  default_enabled: boolean;
  installed_at: string | null;
}

export interface InstallRequest {
  source_url: string;
  default_enabled?: boolean;
}

export interface AccountPluginAction {
  account_ids: number[];
}

export interface SudoUserCreate {
  account_id: number;
  tg_user_id: number;
  display_name?: string;
  allowed_chat_ids?: number[];
  allowed_commands?: string[];
  allow_all_chats?: boolean;
  allow_all_commands?: boolean;
}

export interface SudoUserUpdate {
  display_name?: string;
  allowed_chat_ids?: number[];
  allowed_commands?: string[];
  allow_all_chats?: boolean;
  allow_all_commands?: boolean;
}

export interface SudoUserResponse {
  id: number;
  account_id: number;
  tg_user_id: number;
  display_name?: string;
  allowed_chat_ids?: number[];
  allowed_commands?: string[];
  allow_all_chats: boolean;
  allow_all_commands: boolean;
  created_at: string;
}

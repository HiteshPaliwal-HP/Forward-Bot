import { apiClient } from "./client";

export interface SamplingConfig {
  n: number;
}

export interface TimeWindowConfig {
  timezone: string;
  days_of_week: string[];
  start_time: string;
  end_time: string;
}

export interface AttributionConfig {
  enabled: boolean;
  position: "prefix" | "suffix";
  format: string;
}

export interface AutoReplaceSourceRefsConfig {
  enabled: boolean;
  replacement: string | null;
  replace_display_name: boolean;
}

export interface MediaReplacementConfig {
  enabled: boolean;
  replacement_image_path: string | null;
  replacement_caption_mode: "use_replacement" | "use_source" | "none";
}

export interface ForwardingRule {
  id: string;
  source_id: string;
  destination_channel: string;
  is_active: boolean;
  keyword_match_mode: "literal" | "regex";
  block_keywords: string[];
  allow_keywords: string[];
  media_type_filter: string[];
  remove_links: boolean;
  remove_hashtags: boolean;
  remove_mentions: boolean;
  forward_media: "forward" | "ignore" | "caption_only";
  sampling: SamplingConfig;
  time_window: TimeWindowConfig | null;
  attribution: AttributionConfig;
  auto_replace_source_refs: AutoReplaceSourceRefsConfig;
  media_replacement: MediaReplacementConfig;
  created_at: string;
  updated_at: string;
}

export type RuleCreatePayload = Omit<ForwardingRule, "id" | "created_at" | "updated_at">;
export type RuleUpdatePayload = RuleCreatePayload;

export interface ReplacementRule {
  id: string;
  forwarding_rule_id: string;
  search_text: string;
  replacement_text: string;
  match_mode: "literal" | "regex";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ReplacementRulePayload = Omit<ReplacementRule, "id" | "forwarding_rule_id" | "created_at" | "updated_at">;

export interface RulesListResponse {
  items: ForwardingRule[];
  total: number;
  page: number;
  page_size: number;
}

export const rulesApi = {
  fetchRules: async (params?: { 
    page?: number; 
    page_size?: number; 
    is_active?: boolean;
    source_id?: string;
    folder_id?: string;
  }): Promise<RulesListResponse> => {
    const { data } = await apiClient.get<RulesListResponse>("/rules", { params });
    return data;
  },

  fetchRule: async (id: string): Promise<ForwardingRule> => {
    const { data } = await apiClient.get<ForwardingRule>(`/rules/${id}`);
    return data;
  },

  createRule: async (payload: RuleCreatePayload): Promise<ForwardingRule> => {
    const { data } = await apiClient.post<ForwardingRule>("/rules", payload);
    return data;
  },

  updateRule: async (id: string, payload: RuleUpdatePayload): Promise<ForwardingRule> => {
    const { data } = await apiClient.put<ForwardingRule>(`/rules/${id}`, payload);
    return data;
  },

  deleteRule: async (id: string): Promise<void> => {
    await apiClient.delete(`/rules/${id}`);
  },

  enableRule: async (id: string): Promise<{ ok: boolean }> => {
    const { data } = await apiClient.post<{ ok: boolean }>(`/rules/${id}/enable`);
    return data;
  },

  disableRule: async (id: string): Promise<{ ok: boolean }> => {
    const { data } = await apiClient.post<{ ok: boolean }>(`/rules/${id}/disable`);
    return data;
  },

  fetchReplacementRules: async (ruleId: string): Promise<{ items: ReplacementRule[] }> => {
    const { data } = await apiClient.get<{ items: ReplacementRule[] }>(`/rules/${ruleId}/replacement-rules`);
    return data;
  },

  createReplacementRule: async (ruleId: string, payload: ReplacementRulePayload): Promise<ReplacementRule> => {
    const { data } = await apiClient.post<ReplacementRule>(`/rules/${ruleId}/replacement-rules`, payload);
    return data;
  },

  updateReplacementRule: async (
    ruleId: string,
    replacementId: string,
    payload: ReplacementRulePayload
  ): Promise<ReplacementRule> => {
    const { data } = await apiClient.put<ReplacementRule>(
      `/rules/${ruleId}/replacement-rules/${replacementId}`,
      payload
    );
    return data;
  },

  deleteReplacementRule: async (ruleId: string, replacementId: string): Promise<void> => {
    await apiClient.delete(`/rules/${ruleId}/replacement-rules/${replacementId}`);
  },
};

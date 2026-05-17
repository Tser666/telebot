import { Search } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";

export interface WebSearchFieldsValue {
  web_search: boolean;
  web_search_context_size: "low" | "medium" | "high";
}

export function WebSearchFields({
  value,
  onChange,
}: {
  value: WebSearchFieldsValue;
  onChange: (patch: Partial<WebSearchFieldsValue>) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <Label className="inline-flex items-center gap-1.5 text-sm font-semibold">
            <Search className="h-4 w-4" /> 联网搜索
          </Label>
          <p className="mt-1 text-xs text-muted-foreground">
            开启后，本命令会调用模型的搜索工具并可在模板里用 <code>{"{sources}"}</code> 显示来源。
          </p>
        </div>
        <Switch
          checked={value.web_search}
          onCheckedChange={(v) => onChange({ web_search: v })}
          id="aiWebSearch"
        />
      </div>
      {value.web_search && (
        <div className="grid gap-3 sm:grid-cols-[220px_1fr]">
          <div className="space-y-1.5">
            <Label>搜索上下文强度</Label>
            <Select
              value={value.web_search_context_size}
              onChange={(e) =>
                onChange({
                  web_search_context_size: e.target.value as "low" | "medium" | "high",
                })
              }
            >
              <option value="low">低：更快，更省</option>
              <option value="medium">中：默认平衡</option>
              <option value="high">高：更多上下文</option>
            </Select>
          </div>
          <p className="self-end pb-2 text-xs text-muted-foreground">
            当前后端仅对 OpenAI Responses API 传 <code>web_search</code> 工具。
            选择 Chat Completions 或 Anthropic provider 时会给出明确错误提示。
          </p>
        </div>
      )}
    </div>
  );
}

// 远程插件管理页面
// 支持：从 Git 仓库安装 / 启用 / 禁用 / 更新 / 卸载远程插件
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, GitFork, Package2, RefreshCw, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/misc";
import { getErrMsg } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

import {
  disableRemotePlugin,
  enableRemotePlugin,
  fetchRemotePlugins,
  installRemotePlugin,
  uninstallRemotePlugin,
  updateRemotePlugin,
} from "@/api/remotePlugin";
import type { RemotePlugin } from "@/types/remotePlugin";

const REMOTE_QK = ["remote-plugins"] as const;

export function RemotePlugins() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">远程插件</h1>
        <p className="text-sm text-muted-foreground">
          从 Git 仓库安装、管理第三方插件
        </p>
      </div>
      <InstallBar />
      <RemotePluginList />
    </div>
  );
}

// ── 安装输入栏 ────────────────────────────────────────────────────
function InstallBar() {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");

  const installMut = useMutation({
    mutationFn: () => installRemotePlugin({ source_url: url.trim() }),
    onSuccess: (row) => {
      toast.success(`✅ 已安装 ${row.name} v${row.version}（默认禁用，请手动启用）`);
      setUrl("");
      qc.invalidateQueries({ queryKey: REMOTE_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">从 Git 仓库安装</CardTitle>
        <CardDescription>
          支持 GitHub / GitLab 等公开仓库，仓库根目录需含 <code>plugin.json</code> 或{" "}
          <code>manifest.py</code>
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex gap-2">
          <input
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            placeholder="https://github.com/user/repo.git"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && url.trim()) installMut.mutate();
            }}
            disabled={installMut.isPending}
          />
          <Button
            onClick={() => installMut.mutate()}
            disabled={!url.trim() || installMut.isPending}
            className="shrink-0"
          >
            {installMut.isPending ? (
              <>
                <Spinner className="mr-2 h-4 w-4" />
                安装中…
              </>
            ) : (
              <>
                <Package2 className="mr-2 h-4 w-4" />
                安装
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── 插件列表 ──────────────────────────────────────────────────────
function RemotePluginList() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: REMOTE_QK,
    queryFn: fetchRemotePlugins,
  });

  const enableMut = useMutation({
    mutationFn: (name: string) => enableRemotePlugin(name),
    onSuccess: (_r, name) => {
      toast.success(`已启用 ${name}`);
      qc.invalidateQueries({ queryKey: REMOTE_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const disableMut = useMutation({
    mutationFn: (name: string) => disableRemotePlugin(name),
    onSuccess: (_r, name) => {
      toast.success(`已禁用 ${name}`);
      qc.invalidateQueries({ queryKey: REMOTE_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const updateMut = useMutation({
    mutationFn: (name: string) => updateRemotePlugin(name),
    onSuccess: (row) => {
      toast.success(`已更新 ${row.name} → v${row.version}`);
      qc.invalidateQueries({ queryKey: REMOTE_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const uninstallMut = useMutation({
    mutationFn: (name: string) => uninstallRemotePlugin(name),
    onSuccess: (_r, name) => {
      toast.success(`已卸载 ${name}`);
      qc.invalidateQueries({ queryKey: REMOTE_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Spinner className="text-primary" />
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
        <GitFork className="mx-auto mb-2 h-8 w-8 opacity-30" />
        <p>暂无已安装的远程插件</p>
        <p className="mt-1 text-xs">在上方输入框粘贴 Git 仓库地址开始安装</p>
      </div>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {data.map((plugin) => (
        <PluginCard
          key={plugin.id}
          plugin={plugin}
          onEnable={() => enableMut.mutate(plugin.name)}
          onDisable={() => disableMut.mutate(plugin.name)}
          onUpdate={() => updateMut.mutate(plugin.name)}
          onUninstall={() => {
            if (!confirm(`确认卸载插件「${plugin.name}」？此操作将删除插件文件。`))
              return;
            uninstallMut.mutate(plugin.name);
          }}
          enableLoading={enableMut.isPending && enableMut.variables === plugin.name}
          disableLoading={disableMut.isPending && disableMut.variables === plugin.name}
          updateLoading={updateMut.isPending && updateMut.variables === plugin.name}
          uninstallLoading={uninstallMut.isPending && uninstallMut.variables === plugin.name}
        />
      ))}
    </div>
  );
}

// ── 单个插件卡片 ──────────────────────────────────────────────────
interface PluginCardProps {
  plugin: RemotePlugin;
  onEnable: () => void;
  onDisable: () => void;
  onUpdate: () => void;
  onUninstall: () => void;
  enableLoading?: boolean;
  disableLoading?: boolean;
  updateLoading?: boolean;
  uninstallLoading?: boolean;
}

function PluginCard({
  plugin,
  onEnable,
  onDisable,
  onUpdate,
  onUninstall,
  enableLoading,
  disableLoading,
  updateLoading,
  uninstallLoading,
}: PluginCardProps) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <CardTitle className="truncate text-base">
              {plugin.display_name || plugin.name}
            </CardTitle>
            <p className="font-mono text-xs text-muted-foreground">{plugin.name}</p>
          </div>
          <Badge
            variant={plugin.enabled ? "default" : "outline"}
            className="shrink-0"
          >
            {plugin.enabled ? "已启用" : "已禁用"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        {/* 描述 */}
        {plugin.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {plugin.description}
          </p>
        )}

        {/* 元信息 */}
        <dl className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-muted-foreground">
          {plugin.author && (
            <>
              <dt>作者</dt>
              <dd className="truncate font-medium text-foreground">{plugin.author}</dd>
            </>
          )}
          <dt>版本</dt>
          <dd className="font-medium text-foreground">v{plugin.version}</dd>
          {plugin.installed_at && (
            <>
              <dt>安装时间</dt>
              <dd>{formatDateTime(plugin.installed_at)}</dd>
            </>
          )}
        </dl>

        {/* 来源链接 */}
        <a
          href={plugin.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 truncate text-xs text-muted-foreground hover:text-primary"
        >
          <ExternalLink className="h-3 w-3 shrink-0" />
          {plugin.source_url}
        </a>

        {/* 操作按钮 */}
        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          {plugin.enabled ? (
            <Button
              size="sm"
              variant="outline"
              onClick={onDisable}
              disabled={disableLoading}
            >
              {disableLoading ? <Spinner className="h-3 w-3" /> : "禁用"}
            </Button>
          ) : (
            <Button size="sm" onClick={onEnable} disabled={enableLoading}>
              {enableLoading ? <Spinner className="h-3 w-3" /> : "启用"}
            </Button>
          )}

          <Button
            size="sm"
            variant="outline"
            onClick={onUpdate}
            disabled={updateLoading}
            title="从远程 git pull 更新"
          >
            {updateLoading ? (
              <Spinner className="h-3 w-3" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
            <span className="ml-1">更新</span>
          </Button>

          <Button
            size="sm"
            variant="ghost"
            onClick={onUninstall}
            disabled={uninstallLoading}
            className="text-destructive hover:text-destructive"
            title="卸载并删除插件文件"
          >
            {uninstallLoading ? (
              <Spinner className="h-3 w-3" />
            ) : (
              <Trash2 className="h-3 w-3" />
            )}
            <span className="ml-1">卸载</span>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// 插件中心：合并「功能矩阵」+「已加载插件」+「远程插件」+「开发指南」四处入口
//
// Tab 1：功能矩阵 — 账号 × 功能 启停状态总览
// Tab 2：已加载插件 — 插件列表 + enable/disable + uninstall
// Tab 3：远程插件 — 从 Git 仓库安装/管理远程插件
// Tab 4：开发指南 — react-markdown 渲染 docs/PLUGIN-DEV-GUIDE.md
//
// 之前 /matrix 和 /extensions 两个独立菜单项被砍，访问会 redirect 到这里（App.tsx）。
// 远程插件原为独立 /remote-plugins 页面，现合并到此 Tab。
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  BookOpen,
  Check,
  ExternalLink,
  GitFork,
  Layers,
  Package2,
  Puzzle,
  RefreshCw,
  Trash2,
  X,
} from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github.css";
import devGuideMd from "../../../docs/PLUGIN-DEV-GUIDE.md?raw";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/misc";
import { getFeatureMatrix } from "@/api/features";
import { toggleAccountFeature, cloneConfig } from "@/api/accounts";
import {
  disableInstall,
  enableInstall,
  listInstalledPackages,
  uninstallPlugin,
} from "@/api/plugins";
import {
  fetchRemotePlugins,
  installRemotePlugin,
  enableRemotePlugin,
  disableRemotePlugin,
  updateRemotePlugin,
  uninstallRemotePlugin,
} from "@/api/remotePlugin";
import { getErrMsg } from "@/lib/api";
import type { FeatureMatrixResponse, FeatureState } from "@/api/types";
import type { RemotePlugin } from "@/types/remotePlugin";
import { cn, formatDateTime } from "@/lib/utils";

const PLUGINS_QK = ["plugins", "installed-packages"] as const;
const REMOTE_QK = ["remote-plugins"] as const;

type TabValue = "matrix" | "plugins" | "remote" | "guide";

export function Extensions() {
  const [tab, setTab] = useState<TabValue>("matrix");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">插件中心</h1>
        <p className="text-sm text-muted-foreground">
          功能矩阵 + 插件管理 + 远程插件 + 开发指南
        </p>
      </div>

      <Tabs value={tab} onValueChange={(v) => setTab(v as TabValue)}>
        <TabsList>
          <TabsTrigger value="matrix" className="gap-1.5">
            <Layers className="h-4 w-4" /> 功能矩阵
          </TabsTrigger>
          <TabsTrigger value="plugins" className="gap-1.5">
            <Puzzle className="h-4 w-4" /> 已加载插件
          </TabsTrigger>
          <TabsTrigger value="remote" className="gap-1.5">
            <GitFork className="h-4 w-4" /> 远程插件
          </TabsTrigger>
          <TabsTrigger value="guide" className="gap-1.5">
            <BookOpen className="h-4 w-4" /> 开发指南
          </TabsTrigger>
        </TabsList>

        <TabsContent value="matrix">
          <FeatureMatrixTab />
        </TabsContent>
        <TabsContent value="plugins">
          <PluginsTab />
        </TabsContent>
        <TabsContent value="remote">
          <RemotePluginsTab />
        </TabsContent>
        <TabsContent value="guide">
          <DevGuideTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ── Tab 1：功能矩阵 ────────────────────────────────────────────────
interface CellInfo {
  aid: number;
  aname: string;
  fkey: string;
  fname: string;
  state: FeatureState;
}

function StateIcon({ state }: { state: FeatureState }) {
  if (state === "active")
    return <Check className="mx-auto h-5 w-5 text-emerald-500" />;
  if (state === "failed")
    return <AlertTriangle className="mx-auto h-5 w-5 text-destructive" />;
  return <X className="mx-auto h-5 w-5 text-muted-foreground" />;
}

function FeatureMatrixTab() {
  const nav = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["matrix"],
    queryFn: getFeatureMatrix,
  });

  const [openCell, setOpenCell] = useState<CellInfo | null>(null);
  const [cloneFromAid, setCloneFromAid] = useState<string>("");

  const toggleMut = useMutation({
    mutationFn: async (vars: { aid: number; key: string; enabled: boolean }) =>
      toggleAccountFeature(vars.aid, vars.key, vars.enabled),
    onSuccess: (_d, vars) => {
      toast.success(vars.enabled ? "已启用（worker 激活中…）" : "已禁用");
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["matrix"] });
        qc.invalidateQueries({ queryKey: ["accounts"] });
      }, 1500);
    },
    onError: (err, _vars, ctx) => {
      if ((ctx as any)?.snapshot) qc.setQueryData(["matrix"], (ctx as any).snapshot);
      toast.error(getErrMsg(err));
    },
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: ["matrix"] });
      const snapshot = qc.getQueryData<FeatureMatrixResponse>(["matrix"]);
      if (snapshot) {
        qc.setQueryData<FeatureMatrixResponse>(["matrix"], {
          ...snapshot,
          accounts: snapshot.accounts.map((row) =>
            row.id === vars.aid
              ? {
                  ...row,
                  features: {
                    ...row.features,
                    [vars.key]: vars.enabled ? "active" : "disabled",
                  },
                }
              : row,
          ),
        });
      }
      return { snapshot };
    },
  });

  const cloneMut = useMutation({
    mutationFn: async (vars: { toAid: number; fromAid: number; key: string }) =>
      cloneConfig(vars.toAid, vars.fromAid, [vars.key]),
    onSuccess: () => {
      toast.success("已克隆规则");
      qc.invalidateQueries({ queryKey: ["matrix"] });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">账号 × 功能 矩阵</CardTitle>
        <CardDescription>
          ✓ active · ⚠ failed · ✗ disabled — 点击格子可启停 / 跳配置 / 克隆其他账号规则
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-24 items-center justify-center">
            <Spinner className="text-primary" />
          </div>
        ) : data && data.accounts.length > 0 ? (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>账号 \ 功能</TableHead>
                {data.features.map((f) => (
                  <TableHead key={f.key} className="text-center">
                    {f.display_name}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.accounts.map((row) => (
                <TableRow key={row.id}>
                  <TableCell className="font-medium">{row.name}</TableCell>
                  {data.features.map((f) => {
                    const state = (row.features[f.key] ?? "disabled") as FeatureState;
                    return (
                      <TableCell
                        key={f.key}
                        className={cn(
                          "cursor-pointer text-center hover:bg-accent/50",
                        )}
                        onClick={() =>
                          setOpenCell({
                            aid: row.id,
                            aname: row.name,
                            fkey: f.key,
                            fname: f.display_name,
                            state,
                          })
                        }
                      >
                        <StateIcon state={state} />
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        ) : (
          <p className="py-8 text-center text-sm text-muted-foreground">
            尚未绑定账号
          </p>
        )}
      </CardContent>

      <Dialog open={!!openCell} onOpenChange={(v) => !v && setOpenCell(null)}>
        <DialogContent>
          {openCell && (
            <>
              <DialogHeader>
                <DialogTitle>
                  {openCell.aname} · {openCell.fname}
                </DialogTitle>
                <DialogDescription>当前状态：{openCell.state}</DialogDescription>
              </DialogHeader>

              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {openCell.state !== "active" ? (
                    <Button
                      onClick={() => {
                        toggleMut.mutate({
                          aid: openCell.aid,
                          key: openCell.fkey,
                          enabled: true,
                        });
                        setOpenCell(null);
                      }}
                    >
                      启用
                    </Button>
                  ) : (
                    <Button
                      variant="outline"
                      onClick={() => {
                        toggleMut.mutate({
                          aid: openCell.aid,
                          key: openCell.fkey,
                          enabled: false,
                        });
                        setOpenCell(null);
                      }}
                    >
                      禁用
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={() => {
                      const aid = openCell.aid;
                      const key = openCell.fkey;
                      setOpenCell(null);
                      nav(`/accounts/${aid}/features/${key}`);
                    }}
                  >
                    打开配置页
                  </Button>
                </div>

                <div className="space-y-1.5 border-t pt-3">
                  <p className="text-xs text-muted-foreground">
                    从其他账号复制规则
                  </p>
                  <div className="flex gap-2">
                    <Select
                      value={cloneFromAid}
                      onChange={(e) => setCloneFromAid(e.target.value)}
                    >
                      <option value="">-- 选择来源账号 --</option>
                      {data?.accounts
                        .filter((a) => a.id !== openCell.aid)
                        .map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                    </Select>
                    <Button
                      disabled={!cloneFromAid}
                      onClick={() => {
                        cloneMut.mutate({
                          toAid: openCell.aid,
                          fromAid: Number(cloneFromAid),
                          key: openCell.fkey,
                        });
                        setOpenCell(null);
                        setCloneFromAid("");
                      }}
                    >
                      克隆
                    </Button>
                  </div>
                </div>
              </div>

              <DialogFooter>
                <Button variant="ghost" onClick={() => setOpenCell(null)}>
                  关闭
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

// ── Tab 2：已加载插件 ──────────────────────────────────────────────
function PluginsTab() {
  const qc = useQueryClient();

  const builtinQ = useQuery({
    queryKey: ["matrix"],
    queryFn: getFeatureMatrix,
    select: (data) => data.features.filter((f) => f.is_builtin),
  });

  const thirdPartyQ = useQuery({ queryKey: PLUGINS_QK, queryFn: listInstalledPackages });

  const enableMut = useMutation({
    mutationFn: (key: string) => enableInstall(key),
    onSuccess: (row) => {
      toast.success(`已启用 ${row.key}`);
      qc.invalidateQueries({ queryKey: PLUGINS_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const disableMut = useMutation({
    mutationFn: (key: string) => disableInstall(key),
    onSuccess: (row) => {
      toast.success(`已禁用 ${row.key}`);
      qc.invalidateQueries({ queryKey: PLUGINS_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const uninstallMut = useMutation({
    mutationFn: (key: string) => uninstallPlugin(key),
    onSuccess: (_void, key) => {
      toast.success(`已卸载 ${key}`);
      qc.invalidateQueries({ queryKey: PLUGINS_QK });
    },
    onError: (err) => toast.error(getErrMsg(err)),
  });

  const isLoading = builtinQ.isLoading || thirdPartyQ.isLoading;
  const hasBuiltin = (builtinQ.data ?? []).length > 0;
  const hasThirdParty = (thirdPartyQ.data ?? []).length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">已加载插件</CardTitle>
        <CardDescription>
          builtin 插件 + 从 <code>data/plugins/installed/</code> 加载的第三方插件
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex h-24 items-center justify-center">
            <Spinner className="text-primary" />
          </div>
        ) : !hasBuiltin && !hasThirdParty ? (
          <p className="rounded-md border border-dashed py-8 text-center text-xs text-muted-foreground">
            当前没有已安装插件
          </p>
        ) : (
          <>
            {hasBuiltin && (
              <>
                <div className="mb-2 text-xs font-medium text-muted-foreground">内置插件</div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Key</TableHead>
                      <TableHead>名称</TableHead>
                      <TableHead>类型</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {builtinQ.data!.map((f) => (
                      <TableRow key={f.key}>
                        <TableCell className="font-mono text-xs">{f.key}</TableCell>
                        <TableCell>{f.display_name}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">builtin</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}

            {hasThirdParty && (
              <>
                {hasBuiltin && <div className="my-4 border-t" />}
                <div className="mb-2 text-xs font-medium text-muted-foreground">第三方插件</div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Key</TableHead>
                      <TableHead>版本</TableHead>
                      <TableHead>来源</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>安装时间</TableHead>
                      <TableHead className="text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {thirdPartyQ.data!.map((row) => (
                      <TableRow key={row.key}>
                        <TableCell className="font-mono text-xs">{row.key}</TableCell>
                        <TableCell>{row.version}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{row.source}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant={row.enabled ? "default" : "outline"}>
                            {row.enabled ? "已启用" : "未启用"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {formatDateTime(row.installed_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            {row.enabled ? (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => disableMut.mutate(row.key)}
                                disabled={disableMut.isPending}
                              >
                                禁用
                              </Button>
                            ) : (
                              <Button
                                size="sm"
                                onClick={() => enableMut.mutate(row.key)}
                                disabled={enableMut.isPending}
                              >
                                启用
                              </Button>
                            )}
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                if (!confirm(`确认卸载插件「${row.key}」？`)) return;
                                uninstallMut.mutate(row.key);
                              }}
                              disabled={uninstallMut.isPending}
                            >
                              卸载
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// ── Tab 3：远程插件 ──────────────────────────────────────────────
function RemotePluginsTab() {
  const qc = useQueryClient();
  const [url, setUrl] = useState("");
  const [defaultEnabled, setDefaultEnabled] = useState(false);

  const remoteQ = useQuery({ queryKey: REMOTE_QK, queryFn: fetchRemotePlugins });

  const installMut = useMutation({
    mutationFn: () =>
      installRemotePlugin({ source_url: url.trim(), default_enabled: defaultEnabled }),
    onSuccess: (row) => {
      toast.success(
        defaultEnabled
          ? `已安装 ${row.name} v${row.version}（已为所有账号启用）`
          : `已安装 ${row.name} v${row.version}（默认禁用，请在功能矩阵中按账号启用）`
      );
      setUrl("");
      setDefaultEnabled(false);
      qc.invalidateQueries({ queryKey: REMOTE_QK });
      qc.invalidateQueries({ queryKey: ["matrix"] });
    },
    onError: (err) => toast.error(getErrMsg(err)),
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

  const plugins = remoteQ.data ?? [];

  return (
    <div className="space-y-4">
      {/* 安装输入栏 */}
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
          <label className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              checked={defaultEnabled}
              onChange={(e) => setDefaultEnabled(e.target.checked)}
              className="rounded border-input"
            />
            安装后默认为所有账号启用
          </label>
        </CardContent>
      </Card>

      {/* 插件列表 */}
      {remoteQ.isLoading ? (
        <div className="flex h-32 items-center justify-center">
          <Spinner className="text-primary" />
        </div>
      ) : plugins.length === 0 ? (
        <div className="rounded-lg border border-dashed py-12 text-center text-sm text-muted-foreground">
          <GitFork className="mx-auto mb-2 h-8 w-8 opacity-30" />
          <p>暂无已安装的远程插件</p>
          <p className="mt-1 text-xs">在上方输入框粘贴 Git 仓库地址开始安装</p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {plugins.map((plugin) => (
            <RemotePluginCard
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
      )}
    </div>
  );
}

// ── 远程插件卡片 ──────────────────────────────────────────────────
interface RemotePluginCardProps {
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

function RemotePluginCard({
  plugin,
  onEnable,
  onDisable,
  onUpdate,
  onUninstall,
  enableLoading,
  disableLoading,
  updateLoading,
  uninstallLoading,
}: RemotePluginCardProps) {
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
          {plugin.default_enabled && (
            <Badge variant="secondary" className="shrink-0">默认启用</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3">
        {plugin.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {plugin.description}
          </p>
        )}

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

        <a
          href={plugin.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 truncate text-xs text-muted-foreground hover:text-primary"
        >
          <ExternalLink className="h-3 w-3 shrink-0" />
          {plugin.source_url}
        </a>

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

// ── Tab 4：开发指南 ────────────────────────────────────────────────
function DevGuideTab() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">插件开发指南</CardTitle>
        <CardDescription>
          源文件：<code>docs/PLUGIN-DEV-GUIDE.md</code>，构建时打包进前端
        </CardDescription>
      </CardHeader>
      <CardContent>
        <article className="prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {devGuideMd}
          </ReactMarkdown>
        </article>
      </CardContent>
    </Card>
  );
}

import { Link } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  Braces,
  Cable,
  CheckCircle2,
  ClipboardList,
  GitBranch,
  MousePointerClick,
  Route,
  ShieldCheck,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader, PageShell } from "@/components/layout/PageScaffold";
import { SectionHeader, SignalPill, StatusSummaryPanel, ToneRailCard } from "@/components/ui/status";

const pipeline = [
  { title: "消息渠道", desc: "UserBot、交互 Bot、通知 Bot 都进入统一事件信封。", icon: Cable },
  { title: "插件入口", desc: "插件通过 interaction_entries 声明事件、会话和结果契约。", icon: Braces },
  { title: "动作执行", desc: "ctx.messages 产出标准动作，平台统一校验、限流和发送。", icon: Route },
  { title: "审计收口", desc: "越权通道、按钮错投和未知动作写入运行时日志。", icon: ShieldCheck },
];

const channels = [
  {
    name: "interaction_bot",
    role: "普通 Bot 承接高频群内互动、按钮回调、题面和结果消息。",
  },
  {
    name: "userbot_reply",
    role: "账号 worker 代发低频、敏感或需要人形身份的回复，不承接按钮。",
  },
  {
    name: "bbot_notice",
    role: "通知 Bot 发送转账模拟、结果通知和平台公告，可承接按钮。",
  },
] as const;

const actionRows = [
  ["send_message", "发送或编辑文本消息，可携带 inline keyboard。"],
  ["send_photo / send_file", "发送媒体结果，仍受 send_via 白名单约束。"],
  ["delete_message / pin_message", "删除或置顶交互 Bot 侧消息。"],
  ["answer_callback", "回应普通 Bot 按钮回调，避免插件重复写 Bot API。"],
  ["result / settlement", "汇报成功、会话结束和可对账结算结果。"],
];

export function InteractionIndex() {
  return (
    <PageShell>
      <PageHeader
        icon={Bot}
        title="交互框架"
        description="把 Telegram 消息渠道、插件业务逻辑和平台受控发送能力放到同一个框架页管理。"
        actions={
          <>
            <Button asChild variant="outline" size="sm">
              <Link to="/plugins/manage?tab=guide">插件指南</Link>
            </Button>
            <Button asChild size="sm">
              <Link to="/?accounts=1">
                配置账号
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </>
        }
      />

      <StatusSummaryPanel
        icon={GitBranch}
        title="TelePilot 交互运行面"
        titleLevel="h2"
        description="插件不再需要直接拿 Bot Token、底层客户端或自己拼按钮回调。它声明输入输出契约，平台负责把事件投递给插件，再把标准动作发到正确通道。"
        signals={
          <>
            <SignalPill tone="success" label="事件" value="keyword / message / callback_query" />
            <SignalPill tone="primary" label="发送" value="ctx.messages" />
            <SignalPill tone="warn" label="守卫" value="result_contract.send_via" />
          </>
        }
        aside={
          <div className="w-full rounded-md border border-border/70 bg-background/80 p-3 text-sm">
            <div className="font-semibold">推荐插件模型</div>
            <div className="mt-2 text-muted-foreground">
              UserBot 负责感知和低频身份动作，普通 Bot 负责高频互动，插件只写业务状态机。
            </div>
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-4">
        {pipeline.map((item) => (
          <ToneRailCard
            key={item.title}
            icon={item.icon}
            title={item.title}
            value={<CheckCircle2 className="h-5 w-5 text-emerald-500" />}
            description={item.desc}
            tone="neutral"
            valueClassName="text-sm font-medium text-muted-foreground"
          />
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <Card>
          <CardHeader>
            <SectionHeader
              icon={ClipboardList}
              title="插件动作契约"
              description="插件通过 result_contract 声明能返回什么动作、能走哪些发送通道。运行时会按契约过滤越权动作。"
            />
          </CardHeader>
          <CardContent>
            <div className="overflow-hidden rounded-md border">
              <div className="grid grid-cols-[8rem_minmax(0,1fr)] bg-muted/50 px-3 py-2 text-xs font-semibold text-muted-foreground sm:grid-cols-[12rem_minmax(0,1fr)]">
                <div>动作</div>
                <div>用途</div>
              </div>
              {actionRows.map(([name, desc]) => (
                <div key={name} className="grid grid-cols-[8rem_minmax(0,1fr)] border-t px-3 py-2 text-sm sm:grid-cols-[12rem_minmax(0,1fr)]">
                  <code className="min-w-0 truncate text-xs text-primary">{name}</code>
                  <div className="min-w-0 text-muted-foreground">{desc}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="inline-flex items-center gap-2">
              <MousePointerClick className="h-4 w-4 text-primary" />
              按钮回调
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>按钮点击会作为 callback_query 回到活跃会话。</p>
            <p>插件可用 ctx.messages.answer_callback 回应按钮，再用 ctx.messages.edit 或 send 更新消息。</p>
            <p>userbot_reply 通道会自动移除 reply_markup，防止按钮发到不承接回调的通道。</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {channels.map((item) => (
          <Card key={item.name}>
            <CardHeader>
              <CardTitle className="truncate">
                <code>{item.name}</code>
              </CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-6 text-muted-foreground">{item.role}</CardContent>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}

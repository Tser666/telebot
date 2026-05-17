import {
  OutputTemplateEditor,
  type OutputFormat,
} from "@/components/ai/OutputTemplateEditor";

export interface OutputFormatFieldsValue {
  output_format: OutputFormat;
  output_template: string;
  escape_values: boolean;
}

export function OutputFormatFields({
  value,
  onChange,
}: {
  value: OutputFormatFieldsValue;
  onChange: (patch: Partial<OutputFormatFieldsValue>) => void;
}) {
  return (
    <OutputTemplateEditor
      outputFormat={value.output_format}
      onOutputFormatChange={(v) => onChange({ output_format: v })}
      template={value.output_template}
      onTemplateChange={(v) => onChange({ output_template: v })}
      escapeValues={value.escape_values}
      onEscapeValuesChange={(v) => onChange({ escape_values: v })}
    />
  );
}

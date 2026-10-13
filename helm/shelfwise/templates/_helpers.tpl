{{- define "shelfwise.labels" -}}
app.kubernetes.io/part-of: shelfwise
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "shelfwise.image" -}}
{{ .root.Values.imageRegistry }}/{{ .img.repository }}:{{ .img.tag }}
{{- end -}}

{{- define "shelfwise.dbSecret" -}}{{ .Release.Name }}-postgresql{{- end -}}

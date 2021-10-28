{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "bemcom-app.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create the fully qualified service name used for DNS and stuff.
*/}}
{{- define "bemcom-app.service.fullname" -}}
{{ .fullname }}-{{ .serviceName }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "bemcom-app.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "bemcom-app.labels" -}}
helm.sh/chart: {{ .chart }}
{{ include "bemcom-app.selectorLabels" . }}
{{- if .appVersion }}
app.kubernetes.io/version: {{ .appVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .managedBy }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "bemcom-app.selectorLabels" -}}
app.kubernetes.io/name: {{ .fullname }}
app.kubernetes.io/instance: {{ .fullname }}
bemcom-service-name:  {{ include "bemcom-app.service.fullname" . }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "bemcom-app.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "bemcom-app.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

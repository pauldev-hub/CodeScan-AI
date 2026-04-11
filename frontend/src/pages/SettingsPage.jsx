import { useEffect, useState } from "react";
import { Save, ShieldCheck, User2, WandSparkles } from "lucide-react";

import Button from "../components/Common/Button";
import Card from "../components/Common/Card";
import ScrollReveal from "../components/Common/ScrollReveal";
import { getSettings, updateSettings } from "../services/settingsService";

const SettingsPage = () => {
  const [state, setState] = useState({ loading: true, saving: false, error: "", data: null });

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const payload = await getSettings();
        if (!cancelled) {
          setState({ loading: false, saving: false, error: "", data: payload });
        }
      } catch (error) {
        if (!cancelled) {
          setState((prev) => ({ ...prev, loading: false, error: error?.message || "Unable to load settings" }));
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const updateField = (scope, key, value) => {
    setState((prev) => ({
      ...prev,
      data: {
        ...prev.data,
        [scope]: {
          ...(prev.data?.[scope] || {}),
          [key]: value,
        },
      },
    }));
  };

  const onSave = async () => {
    setState((prev) => ({ ...prev, saving: true, error: "" }));
    try {
      const payload = await updateSettings(state.data);
      setState((prev) => ({ ...prev, saving: false, data: payload }));
    } catch (error) {
      setState((prev) => ({ ...prev, saving: false, error: error?.message || "Unable to save settings" }));
    }
  };

  if (state.loading) {
    return <Card>Loading settings...</Card>;
  }

  return (
    <main className="space-y-5">
      <ScrollReveal className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="overflow-hidden">
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-accent">Settings</p>
          <h1 className="mt-4 text-4xl font-bold leading-tight text-text md:text-5xl">Shape the assistant to match how you work.</h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-text2">
            Update your profile, tune explanation style, and keep the workspace aligned with your learning or shipping mode.
          </p>
        </Card>
        <Card className="bg-[linear-gradient(135deg,rgba(214,161,108,0.16),rgba(255,255,255,0.02))]">
          <div className="flex items-center gap-2 text-accent">
            <WandSparkles size={16} />
            <span className="text-[11px] uppercase tracking-[0.18em]">Assistant profile</span>
          </div>
          <p className="mt-4 text-sm leading-7 text-text2">Persona, explanation depth, beginner mode, and roast mode all feed the new guided results experience.</p>
        </Card>
      </ScrollReveal>

      <div className="grid gap-5 xl:grid-cols-2">
        <ScrollReveal delay={80}>
          <Card>
            <div className="flex items-center gap-2 text-accent">
              <User2 size={16} />
              <span className="text-[11px] uppercase tracking-[0.18em]">Profile</span>
            </div>
            <div className="mt-4 space-y-3">
              <input className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3" value={state.data?.profile?.email || ""} disabled />
              <input
                className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.profile?.name || ""}
                onChange={(event) => updateField("profile", "name", event.target.value)}
                placeholder="Full name"
              />
              <input
                className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.profile?.username || ""}
                onChange={(event) => updateField("profile", "username", event.target.value)}
                placeholder="Username"
              />
              <input
                className="w-full rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.profile?.age ?? ""}
                onChange={(event) => updateField("profile", "age", event.target.value)}
                placeholder="Age"
                type="number"
                min="0"
                max="120"
              />
              <textarea
                className="min-h-[120px] w-full rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.profile?.about_me || ""}
                onChange={(event) => updateField("profile", "about_me", event.target.value)}
                placeholder="About me"
              />
            </div>
          </Card>
        </ScrollReveal>

        <ScrollReveal delay={120}>
          <Card>
            <div className="flex items-center gap-2 text-accent">
              <ShieldCheck size={16} />
              <span className="text-[11px] uppercase tracking-[0.18em]">Preferences</span>
            </div>
            <div className="mt-4 grid gap-3">
              <select
                className="rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.preferences?.persona || "student"}
                onChange={(event) => updateField("preferences", "persona", event.target.value)}
              >
                <option value="student">Student</option>
                <option value="startup founder">Startup founder</option>
                <option value="security engineer">Security engineer</option>
                <option value="staff developer">Staff developer</option>
              </select>
              <select
                className="rounded-2xl border border-border bg-bg3 px-4 py-3"
                value={state.data?.preferences?.explanation_depth || "Beginner"}
                onChange={(event) => updateField("preferences", "explanation_depth", event.target.value)}
              >
                <option value="ELI5">ELI5</option>
                <option value="Beginner">Beginner</option>
                <option value="Developer">Developer</option>
                <option value="Expert">Expert</option>
              </select>
              <label className="flex items-center justify-between rounded-2xl border border-border bg-bg3 px-4 py-3">
                <span className="text-sm text-text">Beginner mode</span>
                <input
                  type="checkbox"
                  checked={Boolean(state.data?.preferences?.beginner_mode)}
                  onChange={(event) => updateField("preferences", "beginner_mode", event.target.checked)}
                />
              </label>
              <label className="flex items-center justify-between rounded-2xl border border-border bg-bg3 px-4 py-3">
                <span className="text-sm text-text">Code roast mode</span>
                <input
                  type="checkbox"
                  checked={Boolean(state.data?.preferences?.roast_mode)}
                  onChange={(event) => updateField("preferences", "roast_mode", event.target.checked)}
                />
              </label>
            </div>
          </Card>
        </ScrollReveal>
      </div>

      <ScrollReveal delay={150}>
        <Card>
          <div className="flex items-center gap-2 text-accent">
            <WandSparkles size={16} />
            <span className="text-[11px] uppercase tracking-[0.18em]">About CodeScan AI</span>
          </div>
          <div className="mt-4 space-y-3 text-sm leading-7 text-text2">
            <p>CodeScan AI is built to make secure coding, debugging, and code review easier for both beginners and experienced developers.</p>
            <p>The workspace combines scan results, guided AI explanations, fix previews, Learn-mode content, and DevChat history inside one dark-mode-first interface.</p>
            <p>Developed by Pratyush Paul.</p>
          </div>
        </Card>
      </ScrollReveal>

      {state.error ? <p className="text-sm text-red">{state.error}</p> : null}
      <div className="flex justify-end">
        <Button isLoading={state.saving} onClick={onSave}>
          Save settings
          <Save size={16} />
        </Button>
      </div>
    </main>
  );
};

export default SettingsPage;

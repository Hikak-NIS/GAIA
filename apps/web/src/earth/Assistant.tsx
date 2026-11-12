import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Mic, Square, Volume2, X, MessageCircle } from "lucide-react";
import { api } from "../api";
import { ErrorBox } from "../pages";

export async function binaryRequest(
  path: string,
  body: unknown,
): Promise<Blob> {
  const response = await fetch("/api/v1" + path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", "X-GAIA-Request": "1" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Не удалось выполнить запрос",
    );
  }
  return response.blob();
}

export function Assistant({
  analysisId,
  territoryId,
}: {
  analysisId?: string;
  territoryId?: string;
}) {
  const [open, setOpen] = useState(false),
    [question, setQuestion] = useState(""),
    [recording, setRecording] = useState(false);
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [error, setError] = useState<unknown>(null),
    [working, setWorking] = useState(false);
  const recorder = useRef<MediaRecorder | null>(null),
    audio = useRef<HTMLAudioElement | null>(null),
    audioUrl = useRef<string | null>(null),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mounted = useRef(true);
  const status = useQuery({
    queryKey: ["integrations-status"],
    queryFn: () => api<{ assistant: boolean }>("/integrations/status"),
    enabled: open,
  });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
      recorder.current?.stream.getTracks().forEach((t) => t.stop());
      if (recorder.current?.state === "recording") recorder.current.stop();
      audio.current?.pause();
      if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
    };
  }, []);
  const chat = useMutation({
    mutationFn: (value: string) =>
      api<{ text: string }>("/assistant/chat", "POST", {
        question: value,
        analysis_id: analysisId,
        territory_id: territoryId,
        history: messages.slice(-8),
      }),
    onSuccess: (data, value) => {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: value },
        { role: "assistant", content: data.text },
      ]);
      setQuestion("");
    },
  });
  async function startRecording() {
    setError(null);
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder)
        throw new Error(
          "Запись требует HTTPS или localhost и браузер с поддержкой микрофона.",
        );
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      const mime = ["audio/webm", "audio/mp4"].find((t) =>
        MediaRecorder.isTypeSupported(t),
      );
      const rec = new MediaRecorder(
        stream,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = rec;
      const chunks: BlobPart[] = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (timer.current) clearTimeout(timer.current);
        if (!mounted.current) return;
        setRecording(false);
        setWorking(true);
        try {
          const form = new FormData();
          form.append(
            "file",
            new Blob(chunks, { type: rec.mimeType }),
            rec.mimeType.includes("mp4") ? "voice.mp4" : "voice.webm",
          );
          const result = await api<{ text: string }>(
            "/assistant/transcribe",
            "POST",
            form,
          );
          if (mounted.current) setQuestion(result.text);
        } catch (e) {
          if (mounted.current) setError(e);
        } finally {
          if (mounted.current) setWorking(false);
        }
      };
      rec.start();
      setRecording(true);
      timer.current = setTimeout(() => {
        if (rec.state === "recording") rec.stop();
      }, 60000);
    } catch (e) {
      setError(e);
    }
  }
  async function speak(text: string) {
    setWorking(true);
    setError(null);
    try {
      const blob = await binaryRequest("/assistant/speech", {
        text: text.slice(0, 4000),
      });
      audio.current?.pause();
      if (audioUrl.current) URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = URL.createObjectURL(blob);
      audio.current = new Audio(audioUrl.current);
      await audio.current.play();
    } catch (e) {
      setError(e);
    } finally {
      setWorking(false);
    }
  }
  return (
    <div className="earth-assistant">
      <button
        className="earth-assistant-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <MessageCircle size={18} />
        ИИ-помощник
      </button>
      {open && (
        <section
          className="earth-assistant-panel"
          aria-label="ИИ-помощник GAIA"
        >
          <header>
            <strong>GAIA · ИИ-помощник</strong>
            <button
              aria-label="Закрыть помощника"
              onClick={() => {
                setOpen(false);
                audio.current?.pause();
                if (recorder.current?.state === "recording")
                  recorder.current.stop();
              }}
            >
              <X size={18} />
            </button>
          </header>
          <p className="global-muted">
            Вопрос, история диалога и выбранные показатели отправляются в
            OpenAI. Запись — до 60 секунд. Ответы и голос создаёт ИИ; выводы
            нужно проверять.
          </p>
          {status.data && !status.data.assistant && (
            <p role="status">
              Добавьте OPENAI_API_KEY в D:\GAIA\.env и перезапустите сервер.
              Ключ вводится только в этот файл.
            </p>
          )}
          <div className="earth-chat-history" aria-live="polite">
            {messages.map((m, i) => (
              <article key={i} className={m.role}>
                <strong>{m.role === "user" ? "Вы" : "GAIA"}</strong>
                <p>{m.content}</p>
                {m.role === "assistant" && (
                  <button
                    className="global-secondary"
                    disabled={working}
                    onClick={() => speak(m.content)}
                  >
                    <Volume2 size={15} />
                    Озвучить
                  </button>
                )}
              </article>
            ))}
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              chat.mutate(question);
            }}
          >
            <label>
              Ваш вопрос
              <textarea
                required
                maxLength={4000}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>
            <div className="earth-button-row">
              <button
                disabled={
                  !status.data?.assistant ||
                  chat.isPending ||
                  working ||
                  recording
                }
              >
                {chat.isPending ? "Готовлю ответ…" : "Отправить"}
              </button>
              <button
                type="button"
                className="global-secondary"
                disabled={!status.data?.assistant || working}
                onClick={() =>
                  recording ? recorder.current?.stop() : startRecording()
                }
              >
                {recording ? <Square size={16} /> : <Mic size={16} />}{" "}
                {recording ? "Закончить запись" : "Голосовой ввод"}
              </button>
              <button
                type="button"
                className="global-secondary"
                onClick={() => audio.current?.pause()}
              >
                Остановить звук
              </button>
            </div>
          </form>
          {working && <p role="status">Обрабатываем аудио…</p>}
          <ErrorBox error={error || chat.error || status.error} />
        </section>
      )}
    </div>
  );
}

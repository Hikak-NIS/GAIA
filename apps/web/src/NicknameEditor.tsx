import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, client } from "./api";
import { ErrorBox, Field } from "./pages";
import type { User } from "./types";

export function NicknameEditor({ user }: { user: User }) {
  const [nickname, setNickname] = useState(user.nickname);
  const save = useMutation({
    mutationFn: () => api<User>("/users/me/nickname", "PUT", { nickname }),
    onSuccess: (data) => client.setQueryData(["me"], data),
  });
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
    >
      <Field label="Ник">
        <input
          required
          minLength={3}
          maxLength={32}
          pattern="[A-Za-z0-9_]{3,32}"
          autoComplete="username"
          value={nickname}
          readOnly={user.role === "superadmin"}
          onChange={(e) => setNickname(e.target.value)}
        />
      </Field>
      <p>
        3–32 символа: латинские буквы, цифры и _. Вход работает по нику или
        email.
      </p>
      {user.role !== "superadmin" && (
        <button disabled={save.isPending}>Сохранить ник</button>
      )}
      <ErrorBox error={save.error} />
      {save.isSuccess && <p role="status">Ник сохранён</p>}
    </form>
  );
}

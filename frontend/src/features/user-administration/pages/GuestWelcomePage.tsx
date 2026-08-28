import React from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../context/AuthContext";
import { Button } from "../../../components/ui/button";

const GuestWelcomePage: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();

  return (
    <div className="flex flex-col items-center justify-center gap-4 min-h-[70vh] p-8 text-center">
      <h1 className="text-2xl font-bold text-foreground">
        {t("guestWelcome.heading")}
      </h1>
      <p className="text-sm text-muted-foreground max-w-md">
        {t("guestWelcome.body")}
      </p>
      <div className="mt-2 flex flex-col items-center gap-1">
        <span className="text-sm font-semibold text-foreground">
          {user?.full_name}
        </span>
        <span className="text-sm text-muted-foreground">{user?.email}</span>
      </div>
      <Button variant="outline" onClick={logout} className="mt-4">
        {t("common.logout")}
      </Button>
    </div>
  );
};

export default GuestWelcomePage;

<?php

namespace App\Message;

class SubscribeNotification
{
    public function __construct(string $email)
    {
        $this->email = $email;
        $this->token = hash('sha256', $email . time());
    }

    public function getEmail(): string
    {
        return $this->email;
    }
    public function getToken(): string
    {
        return $this->token;
    }
}
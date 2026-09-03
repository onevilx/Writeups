<?php

namespace App\MessageHandler;

use Twig\Environment;
use Twig\Loader\FilesystemLoader;
use App\Message\SubscribeNotification;
use Symfony\Component\Messenger\Handler\MessageHandlerInterface;

class SubscribeNotificationHandler implements MessageHandlerInterface
{
    public $email;
    public $token;

    public function __invoke(SubscribeNotification $notification)
    {
        $this->email = $notification->getEmail();
        $this->token = $notification->getToken();
    }

    public function __destruct()
    {
        $this->twig = new \Twig\Environment(new FilesystemLoader(__DIR__ . '/../../templates'));

        $this->body = $this->twig->createTemplate(
            '{% include "email/header.html" %}'.
            '<p>Hi there,</p>'.
            '<p>Please confirm your subscription for Sitelytics Status updates.</p>'.
            '<a href="https://subscribe.sitelytics.htb/confirm?token='.$this->token.'&email='.$this->email.'">'.
            'Confirm Subscription</a><br>'.
            '{% include "email/footer.html" %}'

        )->render();

        mail($this->email, 'Confirm Subscription', $this->body);
    }
}
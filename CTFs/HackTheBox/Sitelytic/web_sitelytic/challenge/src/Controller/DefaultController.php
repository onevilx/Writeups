<?php

namespace App\Controller;

use App\Message\SubscribeNotification;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Messenger\MessageBusInterface;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Validator\Constraints as Assert;
use Symfony\Component\Validator\Validator\ValidatorInterface;
use Doctrine\Persistence\ManagerRegistry;
use App\Repository\ServiceRepository;
use App\Entity\Subscriber;
use App\Entity\Service;

class DefaultController extends AbstractController
{
    private $validator;

    public function __construct(ValidatorInterface $validator)
    {
        $this->validator = $validator;
    }

    public function index(Request $request)
    {
        return $this->render('site/index.html');
    }

    public function loginView(Request $request)
    {
        return $this->render('site/login.html');
    }

    public function listService(Request $request, ServiceRepository $repository)
    {
        $services = $repository->findAll();

        $servicesList = array();
        foreach($services as $item) {
            $servicesList[] = array(
                'service' => $item->getService(),
                'host' => $item->getHost(),
                'headers' => $item->getHeaders(),
                'status' => $item->getStatus(),
            );
        }

        return $this->json($servicesList);
    }

    public function subscribe(Request $request, ManagerRegistry $doctrine, MessageBusInterface $bus)
    {
        $subscribe = json_decode($request->getContent(), false);

        if(! property_exists($subscribe, "email") ) return $this->json(["message" => "Missing required parameters!"], 500);

        $emailConstraint = new Assert\Email();

        $errors = $this->validator->validate(
            $subscribe->email,
            $emailConstraint
        );

        if($errors->count()) {
            return $this->json(["message" => "Invalid email address supplied!"], 401);
        }

        $subscribeNotification = new SubscribeNotification($subscribe->email);

        $entityManager = $doctrine->getManager();

        $subscriberEntity = new Subscriber();
        $subscriberEntity->setEmail($subscribeNotification->getEmail());
        $subscriberEntity->setToken($subscribeNotification->getToken());

        $entityManager->persist($subscriberEntity);
        $entityManager->flush();

        $bus->dispatch($subscribeNotification);

        return $this->json(["message" => "Email subscribed successfully!"]);

    }
}
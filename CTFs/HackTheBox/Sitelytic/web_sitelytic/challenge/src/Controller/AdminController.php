<?php

namespace App\Controller;

use App\Service\ServiceChecker;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Session\SessionInterface;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\RequestStack;
use Doctrine\Persistence\ManagerRegistry;
use App\Repository\ServiceRepository;
use App\Entity\Service;

class AdminController extends AbstractController
{
    private $isLoggedIn;

    public function __construct(RequestStack $requestStack)
    {
        $this->session = $requestStack->getSession();
        $this->isLoggedIn = $this->session->get('loggedin');
    }

    public function adminIndex(Request $request)
    {
        if (!$this->isLoggedIn)
        {
            return $this->redirect('/login?msg=please login first');
        }

        return $this->render('site/admin.html');
    }

    public function saveService(Request $request, ManagerRegistry $doctrine)
    {
        if (!$this->isLoggedIn)
        {
            return $this->redirect('/login?msg=please login first');
        }

        $serviceConfig = json_decode($request->getContent(), false);

        if(!(
            property_exists($serviceConfig, "service") &&
            property_exists($serviceConfig, "headers") &&
            property_exists($serviceConfig, "status")  &&
            property_exists($serviceConfig, "host")
        ))
        {
            return $this->json(["message" => "Missing required parameters!"], 500);
        }

        $entityManager = $doctrine->getManager();
        $service = $entityManager->getRepository(Service::class)->findOneByService($serviceConfig->service);

        if (!$service) {
            return $this->json(["message" => "This service doesn't exist!"], 500);
        }

        $service->setHost($serviceConfig->host);
        $service->setHeaders($serviceConfig->headers);
        $service->setStatus(intval($serviceConfig->status) ? intval($serviceConfig->status) : 1);

        $entityManager->flush();

        return $this->json(["message" => "Settings Saved Successfully!"]);
    }

    public function checkService(Request $request)
    {
        if (!$this->isLoggedIn)
        {
            return $this->redirect('/login?msg=please login first');
        }

        $serviceConfig = json_decode($request->getContent(), false);

        if(!(
            property_exists($serviceConfig, "host") &&
            property_exists($serviceConfig, "headers")
        ))
        {
            return $this->json(["message" => "Missing required parameters!"], 500);
        }

        $serviceChecker = new ServiceChecker(
            $serviceConfig->host,
            $serviceConfig->headers
        );

        if ($serviceChecker->statusLive())
        {
            return $this->json(["message" => "Service is up"]);
        }
        return $this->json(["message" => "Service is down"]);
    }


    public function logout(Request $request)
    {
        $request->getSession()->invalidate();;
        return $this->redirect('/');
    }


}
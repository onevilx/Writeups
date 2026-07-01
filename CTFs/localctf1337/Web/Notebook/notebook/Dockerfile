FROM php:8.2-apache

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip \
    libzip-dev \
    && docker-php-ext-install zip \
    && rm -rf /var/lib/apt/lists/*

COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

COPY composer.json .
RUN composer install --no-dev --optimize-autoloader

COPY index.php .
COPY templates/ templates/

RUN mkdir -p templates_c cache && \
    chown -R www-data:www-data templates_c cache

COPY flag.txt /flag.txt
RUN chmod 444 /flag.txt

RUN sed -i 's/Listen 80/Listen 6969/' /etc/apache2/ports.conf && \
    sed -i 's/:80/:6969/' /etc/apache2/sites-available/000-default.conf

RUN a2enmod rewrite

EXPOSE 6969

CMD ["apache2-foreground"]
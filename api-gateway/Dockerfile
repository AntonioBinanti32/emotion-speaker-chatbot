#TODO: Implementare
FROM nginx:alpine

WORKDIR /etc/nginx

#COPY nginx.conf.template /etc/nginx/nginx.conf.template
#COPY entrypoint.sh /entrypoint.sh

#RUN chmod +x /entrypoint.sh

EXPOSE ${API_GATEWAY_PORT}

#CMD ["/entrypoint.sh"]
COPY nginx.conf /etc/nginx/nginx.conf
CMD ["nginx", "-g", "daemon off;"]
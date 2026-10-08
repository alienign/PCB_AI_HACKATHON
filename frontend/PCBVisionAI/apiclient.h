#ifndef APICLIENT_H
#define APICLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QString>

class ApiClient : public QObject
{
    Q_OBJECT

public:
    explicit ApiClient(QObject *parent = nullptr);

    void uploadImage(const QString &filePath);

signals:
    void imageUploaded(qint64 imageId);
    void uploadFailed(const QString &errorMessage);

private:
    QNetworkAccessManager *networkManager;

    QString baseUrl = "http://127.0.0.1:8000";
};

#endif // APICLIENT_H

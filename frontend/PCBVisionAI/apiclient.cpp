#include "apiclient.h"

#include <QFile>
#include <QFileInfo>
#include <QHttpMultiPart>
#include <QHttpPart>
#include <QJsonDocument>
#include <QJsonObject>
#include <QNetworkReply>
#include <QNetworkRequest>
#include <QUrl>

ApiClient::ApiClient(QObject *parent)
    : QObject(parent)
{
    networkManager = new QNetworkAccessManager(this);
}

void ApiClient::uploadImage(const QString &filePath)
{
    QFileInfo fileInfo(filePath);

    QFile *file = new QFile(filePath);

    if (!file->open(QIODevice::ReadOnly)) {
        emit uploadFailed("Не удалось открыть выбранный файл.");
        file->deleteLater();
        return;
    }

    QHttpMultiPart *multiPart =
        new QHttpMultiPart(QHttpMultiPart::FormDataType);

    QHttpPart filePart;

    QString disposition =
        QString("form-data; name=\"file\"; filename=\"%1\"")
            .arg(fileInfo.fileName());

    filePart.setHeader(
        QNetworkRequest::ContentDispositionHeader,
        disposition
        );

    filePart.setHeader(
        QNetworkRequest::ContentTypeHeader,
        "application/octet-stream"
        );

    file->setParent(multiPart);
    filePart.setBodyDevice(file);

    multiPart->append(filePart);

    QNetworkRequest request(
        QUrl(baseUrl + "/images")
        );

    QNetworkReply *reply =
        networkManager->post(request, multiPart);

    multiPart->setParent(reply);

    connect(
        reply,
        &QNetworkReply::finished,
        this,
        [this, reply]()
        {
            QByteArray responseData = reply->readAll();

            if (reply->error() != QNetworkReply::NoError) {

                QString errorMessage =
                    QString::fromUtf8(responseData);

                if (errorMessage.isEmpty()) {
                    errorMessage = reply->errorString();
                }

                emit uploadFailed(errorMessage);

                reply->deleteLater();
                return;
            }

            QJsonParseError parseError;

            QJsonDocument document =
                QJsonDocument::fromJson(
                    responseData,
                    &parseError
                    );

            if (parseError.error != QJsonParseError::NoError ||
                !document.isObject()) {

                emit uploadFailed(
                    "Backend вернул некорректный ответ."
                    );

                reply->deleteLater();
                return;
            }

            QJsonObject object = document.object();

            if (!object.contains("image_id")) {

                emit uploadFailed(
                    "В ответе backend отсутствует image_id."
                    );

                reply->deleteLater();
                return;
            }

            qint64 imageId =
                object.value("image_id")
                    .toVariant()
                    .toLongLong();

            emit imageUploaded(imageId);

            reply->deleteLater();
        }
        );
}
